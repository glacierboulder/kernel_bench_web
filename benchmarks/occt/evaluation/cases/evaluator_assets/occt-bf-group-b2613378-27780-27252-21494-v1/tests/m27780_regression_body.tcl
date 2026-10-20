puts "BF_CASE_ID=M27780_regression"
pload TOPTEST
plane bf_plane_xy 0 0 0 0 0 1 1 0 0
mkface bf_face_xy bf_plane_xy -1 1 -5 5
plane bf_plane_yz 0 0 0 1 0 0 0 1 0
mkface bf_face_yz bf_plane_yz -5 5 -1 1
set bf_section_log [bsection bf_section bf_face_xy bf_face_yz]
puts "BF_SECTION_LOG_BEGIN"
puts $bf_section_log
puts "BF_SECTION_LOG_END"
puts "BF_SHAPE_CHECK_BEGIN"
checknbshapes bf_section -edge 1 -vertex 2
puts "BF_SHAPE_CHECK_END"
if {[catch {explode bf_section e; mkcurve c_1 bf_section_1; pcurve c2d1 bf_section_1 bf_face_xy; pcurve c2d2 bf_section_1 bf_face_yz; bounds c_1 bf_c3_lo bf_c3_hi; bounds c2d1 bf_1_lo bf_1_hi; bounds c2d2 bf_2_lo bf_2_hi} bf_bounds_error]} {
  puts "BF_ORACLE_EVAL_ERROR=bounds:$bf_bounds_error"
  return
}
foreach name {bf_c3_lo bf_c3_hi bf_1_lo bf_1_hi bf_2_lo bf_2_hi} { set $name [dval $name] }
proc bf_emit_regression_sample {sample} {
  set ratio [expr {$sample / 16.0}]
  set t3 [expr {$::bf_c3_lo + ($::bf_c3_hi - $::bf_c3_lo) * $ratio}]
  set t1 [expr {$::bf_1_lo + ($::bf_1_hi - $::bf_1_lo) * $ratio}]
  set t2 [expr {$::bf_2_lo + ($::bf_2_hi - $::bf_2_lo) * $ratio}]
  uplevel #0 [list cvalue c_1 $t3 x y z dx dy dz]
  puts "BF_REG_STEP_$sample=cvalue"
  set x [uplevel #0 {dval x}]; set y [uplevel #0 {dval y}]; set z [uplevel #0 {dval z}]
  uplevel #0 [list 2dcvalue c2d1 $t1 u1 v1]
  puts "BF_REG_STEP_$sample=pc1"
  set u1 [uplevel #0 {dval u1}]; set v1 [uplevel #0 {dval v1}]
  uplevel #0 [list 2dcvalue c2d2 $t2 u2 v2]
  puts "BF_REG_STEP_$sample=pc2"
  set u2 [uplevel #0 {dval u2}]; set v2 [uplevel #0 {dval v2}]
  uplevel #0 [list svalue bf_plane_xy $u1 $v1 sx1 sy1 sz1]
  set sx1 [uplevel #0 {dval sx1}]; set sy1 [uplevel #0 {dval sy1}]; set sz1 [uplevel #0 {dval sz1}]
  uplevel #0 [list svalue bf_plane_yz $u2 $v2 sx2 sy2 sz2]
  set sx2 [uplevel #0 {dval sx2}]; set sy2 [uplevel #0 {dval sy2}]; set sz2 [uplevel #0 {dval sz2}]
  set r1 [expr {sqrt(($x-$sx1)**2 + ($y-$sy1)**2 + ($z-$sz1)**2)}]
  set r2 [expr {sqrt(($x-$sx2)**2 + ($y-$sy2)**2 + ($z-$sz2)**2)}]
  puts "BF_SAMPLE_$sample=$x,$y,$z,$u1,$v1,$u2,$v2,$r1,$r2"
}
for {set i 0} {$i <= 16} {incr i} {
  if {[catch {bf_emit_regression_sample $i} bf_sample_error bf_sample_options]} {
    puts "BF_ORACLE_EVAL_ERROR=sample_$i:$bf_sample_error"
    if {[dict exists $bf_sample_options -errorinfo]} { puts "BF_ORACLE_ERRORINFO=[dict get $bf_sample_options -errorinfo]" }
    return
  }
}
puts "BF_TCL_SAMPLING_COMPLETE=1"
