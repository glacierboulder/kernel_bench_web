source [file join [file dirname [file normalize [info script]]] neighbor_support.tcl]

pload MODELING

proc mn_check_m30082_residual {issue_version scale angle dx dy dz suffix} {
  mn_load_fixture mantis-30082 $issue_version
  mn_restore_b64 $::fixture_bug27928_b1_brep b1_$suffix m30082a_$suffix
  mn_restore_b64 $::fixture_bug27928_b2_brep b2_$suffix m30082b_$suffix
  set source_a b1_$suffix
  set source_b b2_$suffix
  uplevel #0 [list explode $source_a f]
  uplevel #0 [list explode $source_b f]
  set original_sf1 original_surface1_$suffix
  set original_sf2 original_surface2_$suffix
  uplevel #0 [list mksurface $original_sf1 ${source_a}_1]
  uplevel #0 [list mksurface $original_sf2 ${source_b}_2]
  set transformed_a transformed_a_$suffix
  set transformed_b transformed_b_$suffix
  uplevel #0 [list copy $source_a $transformed_a]
  uplevel #0 [list copy $source_b $transformed_b]
  set a $transformed_a
  set b $transformed_b
  foreach shape [list $a $b] {
    uplevel #0 [list tscale $shape 0 0 0 $scale]
    uplevel #0 [list trotate $shape 0 0 0 1 2 3 $angle]
    uplevel #0 [list ttranslate $shape $dx $dy $dz]
  }
  uplevel #0 [list explode $a f]
  uplevel #0 [list explode $b f]
  set sf1 surface1_$suffix
  set sf2 surface2_$suffix
  uplevel #0 [list mksurface $sf1 ${a}_1]
  uplevel #0 [list mksurface $sf2 ${b}_2]
  mn_assert_transformed_surface_point $original_sf1 $sf1 0.2 0.0 $scale $angle $dx $dy $dz "$suffix surface1"
  mn_assert_transformed_surface_point $original_sf2 $sf2 0.2 0.0 $scale $angle $dx $dy $dz "$suffix surface2"
  set log [uplevel #0 [list bopcurves ${a}_1 ${b}_2 -2d]]
  set count [mn_report_intersection $log 1 "M30082 scale=$scale transform=$suffix"]
  if {$count != 1} { return }
  mn_assert_absolute_cap_independent_of_reported_tolerance $scale $suffix

  set curveRoot curve_$suffix
  mn_retain_curves c $curveRoot $count
  set curve ${curveRoot}_1
  set length_report [uplevel #0 [list length $curve]]
  if {[regexp {is[[:space:]]+([-+0-9.eE]+)} $length_report -> length_value]} {
    bench_assert_range $length_value 1.0e-8 1.0e100 "M30082 $suffix finite positive curve length"
  } else {
    bench_assert {0} "M30082 $suffix curve length is measurable"
  }

  set forward_length $length_value
  mn_check_residual_with_reported_tolerance $curve $sf1 $scale "$suffix forward surface1"
  mn_check_residual_with_reported_tolerance $curve $sf2 $scale "$suffix forward surface2"

  # Swap the surface order to exercise the same physical branch under the
  # inverse operand ordering; preserve and compare each result independently.
  set reverse_log [uplevel #0 [list bopcurves ${b}_2 ${a}_1 -2d]]
  set reverse_count [mn_report_intersection $reverse_log 1 "M30082 reverse order scale=$scale transform=$suffix"]
  if {$reverse_count != 1} { return }
  set reverse_root reverse_curve_$suffix
  mn_retain_curves c $reverse_root $reverse_count
  set reverse_curve ${reverse_root}_1
  set reverse_length_report [uplevel #0 [list length $reverse_curve]]
  if {[regexp {is[[:space:]]+([-+0-9.eE]+)} $reverse_length_report -> reverse_length]} {
    bench_assert_close $reverse_length $forward_length [expr {1.0e-5 * max(1.0,$scale)}] \
      "M30082 $suffix operand-order length invariant"
  } else {
    bench_assert {0} "M30082 $suffix reverse curve length is measurable"
  }
  mn_check_residual_with_reported_tolerance $reverse_curve $sf1 $scale "$suffix reverse surface1"
  mn_check_residual_with_reported_tolerance $reverse_curve $sf2 $scale "$suffix reverse surface2"
}

# Use one scale change and one common rigid transform to probe the same
# cylinder-cylinder endpoint mechanism across physical size and world pose.
mn_check_m30082_residual 2 0.5 31 250 -80 40 half_scale_rotated
mn_check_m30082_residual 2 2.0 67 -120 55 18 double_scale_rotated
bench_finish
