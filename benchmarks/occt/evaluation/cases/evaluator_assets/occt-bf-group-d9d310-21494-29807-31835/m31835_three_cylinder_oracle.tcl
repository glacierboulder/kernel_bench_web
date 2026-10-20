# Hidden geometric oracle for declared three-cylinder common calibrations.
proc bf_check_common_result {theShape theExpectedVolume theRelativeVolumeTolerance} {
  set shape_rc [catch {uplevel #0 [list checkshape $theShape]} shape_result]
  puts "BF_CHECKSHAPE_RC_$theShape=$shape_rc"
  puts "BF_CHECKSHAPE_RESULT_$theShape=$shape_result"
  if {$shape_rc != 0 || ![regexp {valid|looks OK} $shape_result]} {
    puts "Error: BF shape validity check failed for $theShape"
  }
  set check_result [uplevel #0 [list bopcheck $theShape]]
  puts "BF_BOPCHECK=$check_result"
  if {![regexp {OK} $check_result]} {
    puts "Error: BF common result fails BOP validity"
  }
  uplevel #0 [list checknbshapes $theShape -solid 1]
  # -eps controls property computation precision; -deps is the comparison
  # threshold used by checkprops. Set both explicitly so the declared relative
  # geometry tolerance is actually enforced rather than the 1% default.
  uplevel #0 [list checkprops $theShape -v $theExpectedVolume \
                -eps $theRelativeVolumeTolerance -deps $theRelativeVolumeTolerance]
}

plane p1 [expr {-$bf_length/2.0}] 0 0 1 0 0
pcylinder c1 p1 $bf_radius $bf_length
plane p2 0 0 [expr {-$bf_length/2.0}] 0 0 1
pcylinder c2 p2 $bf_radius $bf_length
plane p3 $bf_offset [expr {$bf_length/2.0}] 0 0 -1 0
pcylinder c3 p3 $bf_radius $bf_length

puts "BF_INPUT_C1=[whatis c1]"
puts "BF_INPUT_C2=[whatis c2]"
puts "BF_INPUT_C3=[whatis c3]"

bcommon r c1 c2
puts "BF_FIRST_COMMON_SHAPE=[whatis r]"
bf_check_common_result r $bf_expected_first_volume $bf_relative_volume_tolerance
bcommon result r c3
puts "BF_FINAL_COMMON_SHAPE=[whatis result]"
bf_check_common_result result $bf_expected_volume $bf_relative_volume_tolerance
puts "BF_FIRST_COMMON_VOLUME_EXPECTED=$bf_expected_first_volume"
puts "BF_FINAL_COMMON_VOLUME_EXPECTED=$bf_expected_volume"
puts "BF_HIDDEN_GEOMETRY_ORACLE=checked"
