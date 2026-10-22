set here [file dirname [file normalize [info script]]]
set helper [file join $here neighbor_support.tcl]
if {![file isfile $helper]} {
  set helper [file join [file dirname [file dirname $here]] mantis-30082 5 neighbor_support.tcl]
}
source $helper

pload MODELING

proc mn_check_m31602_seam_matrix {scale angle dx dy dz suffix} {
  mn_load_fixture mantis-31602 2
  mn_restore_b64 $::fixture_bug31602_brep f "m31602_$suffix"
  uplevel #0 [list explode f f]
  uplevel #0 [list copy f_1 f1_$suffix]
  uplevel #0 [list copy f_2 f2_$suffix]
  set face1 f1_$suffix
  set face2 f2_$suffix

  foreach face [list $face1 $face2] {
    uplevel #0 [list tscale $face 0 0 0 $scale]
    uplevel #0 [list trotate $face 0 0 0 1 2 3 $angle]
    uplevel #0 [list ttranslate $face $dx $dy $dz]
  }
  set sf1 surface1_$suffix
  set sf2 surface2_$suffix
  uplevel #0 [list mksurface $sf1 $face1]
  uplevel #0 [list mksurface $sf2 $face2]

  set report [uplevel #0 [list bopcurves $face1 $face2 -2d]]
  set count [mn_report_intersection $report 1 "M31602 scale=$scale pose=$suffix forward order"]
  if {$count != 1} { return }
  set root forward_curve_$suffix
  mn_retain_curves c $root $count
  set curve ${root}_1
  set forward_length [mn_curve_length $curve]
  bench_assert_range [expr {double($::mn_last_reported_tolerance)}] 0.0 [expr {3.0e-6*max(1.0,$scale)}] \
    "M31602 $suffix forward reported tolerance stays in issue range"

  foreach surface [list $sf1 $sf2] {
    set physical_max [mn_physical_residual_max $curve $surface 201 "$suffix forward $surface"]
    bench_assert_range $physical_max 0.0 [expr {3.0e-6*max(1.0,$scale)}] \
      "M31602 $suffix forward curve samples remain on $surface"
  }

  set reverse_report [uplevel #0 [list bopcurves $face2 $face1 -2d]]
  set reverse_count [mn_report_intersection $reverse_report 1 "M31602 scale=$scale pose=$suffix reverse order"]
  if {$reverse_count != 1} { return }
  set reverse_root reverse_curve_$suffix
  mn_retain_curves c $reverse_root $reverse_count
  set reverse_curve ${reverse_root}_1
  set reverse_length [mn_curve_length $reverse_curve]
  bench_assert_close $reverse_length $forward_length [expr {0.05*max(1.0,$scale)}] \
    "M31602 $suffix operand-order length invariant"
  foreach surface [list $sf1 $sf2] {
    set physical_max [mn_physical_residual_max $reverse_curve $surface 201 "$suffix reverse $surface"]
    bench_assert_range $physical_max 0.0 [expr {3.0e-6*max(1.0,$scale)}] \
      "M31602 $suffix reverse curve samples remain on $surface"
  }

  set expected_length [expr {1340.6982492258749*$scale}]
  bench_assert_close $forward_length $expected_length [expr {0.1*max(1.0,$scale)}] \
    "M31602 $suffix scaled physical branch length"
}

# Scale crosses two magnitudes; rotations and translations perturb world-space
# coordinates while reversed face order probes parameter/seam bookkeeping.
mn_check_m31602_seam_matrix 0.5 29 45 -22 13 half_scale_rotated
mn_check_m31602_seam_matrix 2.0 83 -140 65 28 double_scale_rotated

bench_finish
