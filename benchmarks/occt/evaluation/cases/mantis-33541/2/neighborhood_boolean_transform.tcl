set here [file dirname [file normalize [info script]]]
set helper [file join $here neighbor_support.tcl]
if {![file isfile $helper]} {
  set helper [file join [file dirname [file dirname $here]] mantis-30082 5 neighbor_support.tcl]
}
source $helper

pload MODELING

proc mn_check_m33541_boolean_matrix {scale angle dx dy dz suffix} {
  set cylinder cylinder_$suffix
  set sphere sphere_$suffix
  set cut cut_$suffix
  set common common_$suffix
  set reverse reverse_$suffix

  uplevel #0 [list pcylinder $cylinder 1.0 1.0]
  uplevel #0 [list psphere $sphere 1.0]
  foreach shape [list $cylinder $sphere] {
    uplevel #0 [list tscale $shape 0 0 0 $scale]
  }
  # Scale the source separation as well as the primitive radii; tscale on a
  # translated shape in this OCCT/DRAW combination leaves its placement out
  # of the intended similarity transform.
  uplevel #0 [list ttranslate $sphere $scale $scale $scale]
  foreach shape [list $cylinder $sphere] {
    uplevel #0 [list trotate $shape 0 0 0 1 2 3 $angle]
    uplevel #0 [list ttranslate $shape $dx $dy $dz]
  }

  uplevel #0 [list bcut $cut $cylinder $sphere]
  uplevel #0 [list bcommon $common $cylinder $sphere]
  uplevel #0 [list bcut $reverse $sphere $cylinder]
  foreach result [list $cut $common $reverse] {
    mn_shape_valid $result "M33541 $suffix $result"
  }

  set factor [expr {$scale*$scale*$scale}]
  set expected_cut [expr {2.8126*$factor}]
  set expected_common [expr {0.328988*$factor}]
  set expected_reverse [expr {(4.1887902047863905-0.328988)*$factor}]
  set cut_volume [mn_shape_volume $cut]
  set common_volume [mn_shape_volume $common]
  set reverse_volume [mn_shape_volume $reverse]
  puts "MN_M33541_VOLUMES suffix=$suffix scale=$scale cut=$cut_volume common=$common_volume reverse_cut=$reverse_volume"
  bench_assert_close $cut_volume $expected_cut [expr {0.001*$factor}] \
    "M33541 $suffix analytic scaled cut volume"
  bench_assert_close $common_volume $expected_common [expr {0.0002*$factor}] \
    "M33541 $suffix analytic scaled Common volume"
  bench_assert_close $reverse_volume $expected_reverse [expr {0.001*$factor}] \
    "M33541 $suffix reversed cut volume"
}

# The expected physical measures come from the issue's cylinder/sphere input.
# Uniform scaling must change volume cubically; a shared rigid pose and operand
# reversal must preserve the corresponding set difference/intersection.
mn_check_m33541_boolean_matrix 0.5 31 80 -45 22 half_scale_pose_a
mn_check_m33541_boolean_matrix 1.5 67 -120 35 19 enlarged_pose_b

bench_finish
