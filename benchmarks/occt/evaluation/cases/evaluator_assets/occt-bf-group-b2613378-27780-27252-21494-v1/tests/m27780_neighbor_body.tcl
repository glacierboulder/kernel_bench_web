puts "BF_CASE_ID=M27780_F_neighbor"
pload TOPTEST
set bf_input_dir [file normalize [file join [file dirname [info script]] .. inputs]]
restore [file join $bf_input_dir buc60532a.brep] p
restore [file join $bf_input_dir buc60532b.brep] t1
explode t1 f
ttranslate t1_2 0.05 0 0
mksurface bf_surface1 p
mksurface bf_surface2 t1_2
set bf_bop_log [bopcurves p t1_2 -2d -p 6.2406621764215551 0.23999999463558200 0.00034444887595448459 -5.0019657458625186]
puts "BF_BOP_LOG_BEGIN"
puts $bf_bop_log
puts "BF_BOP_LOG_END"
if {![regexp {([0-9]+) curve\(s\) found} $bf_bop_log -> bf_curve_count]} {
  puts "BF_ORACLE_EVAL_ERROR=curve_count_not_found"
  return
}
puts "BF_CURVE_COUNT=$bf_curve_count"
if {$bf_curve_count < 1} {
  puts "BF_ORACLE_EVAL_ERROR=selected_branch_missing"
  return
}
if {[catch {bounds c_1 bf_c3_lo bf_c3_hi; bounds c2d1_1 bf_1_lo bf_1_hi; bounds c2d2_1 bf_2_lo bf_2_hi} bf_bounds_error]} {
  puts "BF_ORACLE_EVAL_ERROR=bounds:$bf_bounds_error"
  return
}
foreach name {bf_c3_lo bf_c3_hi bf_1_lo bf_1_hi bf_2_lo bf_2_hi} {
  set $name [dval $name]
}
puts "BF_C3_RANGE=$bf_c3_lo,$bf_c3_hi"
puts "BF_PC1_RANGE=$bf_1_lo,$bf_1_hi"
puts "BF_PC2_RANGE=$bf_2_lo,$bf_2_hi"
proc bf_emit_m27780_sample {sample} {
  set ratio [expr {$sample / 16.0}]
  set t3 [expr {$::bf_c3_lo + ($::bf_c3_hi - $::bf_c3_lo) * $ratio}]
  set t1 [expr {$::bf_1_lo + ($::bf_1_hi - $::bf_1_lo) * $ratio}]
  set t2 [expr {$::bf_2_lo + ($::bf_2_hi - $::bf_2_lo) * $ratio}]
  uplevel #0 [list cvalue c_1 $t3 x3 y3 z3 dx dy dz]
  puts "BF_STEP_$sample=cvalue"
  set x3 [uplevel #0 {dval x3}]; set y3 [uplevel #0 {dval y3}]; set z3 [uplevel #0 {dval z3}]
  uplevel #0 [list 2dcvalue c2d1_1 $t1 u1 v1]
  puts "BF_STEP_$sample=pc1"
  set u1 [uplevel #0 {dval u1}]; set v1 [uplevel #0 {dval v1}]
  uplevel #0 [list 2dcvalue c2d2_1 $t2 u2 v2]
  puts "BF_STEP_$sample=pc2"
  set u2 [uplevel #0 {dval u2}]; set v2 [uplevel #0 {dval v2}]
  uplevel #0 [list svalue bf_surface1 $u1 $v1 sx1 sy1 sz1]
  puts "BF_STEP_$sample=s1"
  set sx1 [uplevel #0 {dval sx1}]; set sy1 [uplevel #0 {dval sy1}]; set sz1 [uplevel #0 {dval sz1}]
  uplevel #0 [list svalue bf_surface2 $u2 $v2 sx2 sy2 sz2]
  puts "BF_STEP_$sample=s2"
  set sx2 [uplevel #0 {dval sx2}]; set sy2 [uplevel #0 {dval sy2}]; set sz2 [uplevel #0 {dval sz2}]
  set r1 [expr {sqrt(($x3-$sx1)**2 + ($y3-$sy1)**2 + ($z3-$sz1)**2)}]
  set r2 [expr {sqrt(($x3-$sx2)**2 + ($y3-$sy2)**2 + ($z3-$sz2)**2)}]
  puts "BF_SAMPLE_$sample=$x3,$y3,$z3,$u1,$v1,$u2,$v2,$r1,$r2"
}
for {set i 0} {$i <= 16} {incr i} {
  if {[catch {bf_emit_m27780_sample $i} bf_sample_error bf_sample_options]} {
    puts "BF_ORACLE_EVAL_ERROR=sample_$i:$bf_sample_error"
    if {[dict exists $bf_sample_options -errorinfo]} { puts "BF_ORACLE_ERRORINFO=[dict get $bf_sample_options -errorinfo]" }
    return
  }
}
trim bf_trimmed c2d1_1 0 1
2dcvalue bf_trimmed 0 bf_u0 bf_v0
2dcvalue bf_trimmed 1 bf_u1 bf_v1 bf_du bf_dv
set bf_u0 [dval bf_u0]; set bf_v0 [dval bf_v0]
set bf_u1 [dval bf_u1]; set bf_v1 [dval bf_v1]
set bf_du [dval bf_du]; set bf_dv [dval bf_dv]
set bf_direction_dot [expr {($bf_u1-$bf_u0)*$bf_du + ($bf_v1-$bf_v0)*$bf_dv}]
puts "BF_DIRECTION_DOT=$bf_direction_dot"
puts "BF_TCL_SAMPLING_COMPLETE=1"
