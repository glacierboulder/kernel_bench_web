pload TOPTEST
set occ496a [locate_data_file OCC496a.brep]
set occ496b [locate_data_file OCC496b.brep]
restore $occ496a a
restore $occ496b b
explode a f
explode b f
ttranslate b_2 1.8 0.5 0
puts "BF_CASE=M27310_finite_face_neighborhood"
puts "BF_EXPECT_CURVES=1"
puts "BF_INPUT_A_FACE=a_8"
puts "BF_INPUT_B_FACE=b_2_translated_1.8_0.5_0"
set bf_intersection_log [bopcurves a_8 b_2 -2d]
puts "BF_BOPCURVES_BEGIN"
puts $bf_intersection_log
puts "BF_BOPCURVES_END"
if {[regexp {([0-9]+) curve\(s\) found} $bf_intersection_log -> bf_curve_count]} {
  puts "BF_CURVE_COUNT=$bf_curve_count"
} elseif {[string first "has no 3d curves" $bf_intersection_log] >= 0} {
  puts "BF_CURVE_COUNT=0"
} else {
  puts "BF_ORACLE_EVAL_ERROR=curve_count_unreadable"
  return
}
proc bf_emit_samples {theCurve theIndex} {
  uplevel #0 [list bounds $theCurve U1 U2]
  set u1 [uplevel #0 {dval U1}]
  set u2 [uplevel #0 {dval U2}]
  if {![string is double -strict $u1] || ![string is double -strict $u2] || $u2 <= $u1} {
    return -code error "BF_ORACLE_EVAL_ERROR: invalid bounds for $theCurve"
  }
  puts "BF_CURVE_${theIndex}_RANGE=$u1,$u2"
  for {set sample 0} {$sample <= 16} {incr sample} {
    set parameter [expr {$u1+($u2-$u1)*$sample/16.0}]
    uplevel #0 [list cvalue $theCurve $parameter x y z dx dy dz]
    set xv [uplevel #0 {dval x}]
    set yv [uplevel #0 {dval y}]
    set zv [uplevel #0 {dval z}]
    if {![string is double -strict $xv] || ![string is double -strict $yv] || ![string is double -strict $zv]} {
      return -code error "BF_ORACLE_EVAL_ERROR: unreadable point at $theCurve sample $sample"
    }
    puts "BF_CURVE_${theIndex}_SAMPLE_${sample}=$xv,$yv,$zv"
  }
}
for {set i 1} {$i <= $bf_curve_count} {incr i} {
  if {[catch {bf_emit_samples c_$i $i} bf_sample_error]} {
    puts $bf_sample_error
    return
  }
}
puts "BF_TCL_SAMPLING_COMPLETE=1"
