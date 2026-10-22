# Generic, case-independent assertions shared by the BF neighborhood scripts.
namespace eval ::bench {
  variable assertions 0
  variable numeric_assertions 0
  variable failures 0
}

proc ::bench::_record {kind passed label detail} {
  variable assertions
  variable numeric_assertions
  variable failures
  incr assertions
  if {$kind eq "numeric"} { incr numeric_assertions }
  if {$passed} {
    puts "BENCH_ASSERT_PASS kind=$kind label=[list $label] detail=[list $detail]"
  } else {
    incr failures
    puts stderr "BENCH_ASSERT_FAIL kind=$kind label=[list $label] detail=[list $detail]"
  }
  return [expr {$passed ? 1 : 0}]
}

proc bench_assert {expression label} {
  if {[catch {uplevel 1 [list expr $expression]} value]} {
    return [::bench::_record expression 0 $label "evaluation_error=$value"]
  }
  return [::bench::_record expression [expr {$value ? 1 : 0}] $label "value=$value"]
}

proc bench_is_finite {value} {
  if {![string is double -strict $value]} { return 0 }
  if {[catch {expr {abs(double($value)) <= 1.7976931348623157e308}} finite] || !$finite} {
    return 0
  }
  return 1
}

proc bench_assert_close {actual expected tolerance label} {
  foreach value [list $actual $expected $tolerance] {
    if {![bench_is_finite $value]} {
      return [::bench::_record numeric 0 $label \
        "actual=$actual expected=$expected tolerance=$tolerance non_finite_or_non_numeric"]
    }
  }
  if {[catch {expr {double($tolerance) >= 0.0}} valid_tolerance] || !$valid_tolerance} {
    return [::bench::_record numeric 0 $label \
      "actual=$actual expected=$expected tolerance=$tolerance invalid_tolerance"]
  }
  set error [expr {abs(double($actual) - double($expected))}]
  return [::bench::_record numeric [expr {$error <= double($tolerance)}] $label \
    "actual=$actual expected=$expected tolerance=$tolerance absolute_error=$error"]
}

proc bench_finish {} {
  variable ::bench::assertions
  variable ::bench::numeric_assertions
  variable ::bench::failures
  if {$assertions < 1} { return -code error "bench_finish requires at least one assertion" }
  if {$failures != 0} {
    puts stderr "BENCH_ORACLE_FAILED assertions=$assertions failures=$failures"
    return -code error "one or more benchmark assertions failed"
  }
  puts "BENCH_ORACLE_OK assertions=$assertions numeric_assertions=$numeric_assertions"
  puts "TEST_DONE assertions=$assertions numeric_assertions=$numeric_assertions"
}

proc bench_curve_names {root {limit 64}} {
  set result {}
  for {set i 1} {$i <= $limit} {incr i} {
    if {[catch {uplevel #0 [list whatis ${root}_$i]} kind] || [string first "3d curve" $kind] < 0} { break }
    lappend result ${root}_$i
  }
  return $result
}

proc bench_curve_bounds {curve} {
  uplevel #0 [list bounds $curve bench_u1 bench_u2]
  set u1 [uplevel #0 {dval bench_u1}]
  set u2 [uplevel #0 {dval bench_u2}]
  if {![bench_is_finite $u1] || ![bench_is_finite $u2] || $u2 <= $u1} {
    return -code error "invalid or unreadable parameter bounds for $curve"
  }
  return [list $u1 $u2]
}

proc bench_curve_point {curve parameter} {
  uplevel #0 [list cvalue $curve $parameter bench_x bench_y bench_z bench_dx bench_dy bench_dz]
  set point [list [uplevel #0 {dval bench_x}] [uplevel #0 {dval bench_y}] [uplevel #0 {dval bench_z}]]
  foreach value $point {
    if {![bench_is_finite $value]} { return -code error "non-finite or unreadable 3D sample on $curve" }
  }
  return $point
}

proc bench_distance3 {a b} {
  lassign $a ax ay az
  lassign $b bx by bz
  foreach value [list $ax $ay $az $bx $by $bz] {
    if {![bench_is_finite $value]} { return -code error "distance input contains a non-finite coordinate" }
  }
  set distance [expr {sqrt(($ax-$bx)**2 + ($ay-$by)**2 + ($az-$bz)**2)}]
  if {![bench_is_finite $distance]} { return -code error "distance calculation produced a non-finite result" }
  return $distance
}

proc bench_curve_distance_min {curve point {samples 257}} {
  lassign [bench_curve_bounds $curve] u1 u2
  set nearest 1.0e100
  for {set i 0} {$i < $samples} {incr i} {
    set parameter [expr {$u1+($u2-$u1)*$i/double($samples-1)}]
    set distance [bench_distance3 [bench_curve_point $curve $parameter] $point]
    if {$distance < $nearest} { set nearest $distance }
  }
  return $nearest
}

proc bench_closed_curve_gap {curve} {
  lassign [bench_curve_bounds $curve] u1 u2
  return [bench_distance3 [bench_curve_point $curve $u1] [bench_curve_point $curve $u2]]
}

proc bench_support_distance_scan {curve surface tolerance {samples 101}} {
  lassign [bench_curve_bounds $curve] u1 u2
  uplevel #0 [list xdistcs $curve $surface $u1 $u2 $samples $tolerance]
  for {set i 0} {$i < $samples} {incr i} {
    set parameter [expr {$u1+($u2-$u1)*$i/double($samples-1)}]
    bench_curve_point $curve $parameter
  }
  return $samples
}

proc bench_surface_xyz {surface u v} {
  uplevel #0 [list svalue $surface $u $v bench_sx bench_sy bench_sz]
  set point [list [uplevel #0 {dval bench_sx}] [uplevel #0 {dval bench_sy}] [uplevel #0 {dval bench_sz}]]
  foreach value $point {
    if {![bench_is_finite $value]} { return -code error "non-finite or unreadable surface sample on $surface" }
  }
  return $point
}

proc bench_surface_transformed_uv {source_surface transformed_surface u v scale tx ty tz tolerance label} {
  lassign [bench_surface_xyz $source_surface $u $v] sx sy sz
  set expected [list [expr {$scale*$sx+$tx}] [expr {$scale*$sy+$ty}] [expr {$scale*$sz+$tz}]]
  set best_u $u
  set best_v $v
  set best_residual 1.0e100
  foreach factors {{1.0 1.0} {1.0 0.0} {0.0 1.0} {0.0 0.0}} {
    lassign $factors u_scaled v_scaled
    set candidate_u [expr {$u*(1.0+$u_scaled*($scale-1.0))}]
    set candidate_v [expr {$v*(1.0+$v_scaled*($scale-1.0))}]
    set observed [bench_surface_xyz $transformed_surface $candidate_u $candidate_v]
    set residual [bench_distance3 $observed $expected]
    if {$residual < $best_residual} {
      set best_residual $residual
      set best_u $candidate_u
      set best_v $candidate_v
    }
  }
  puts "BF_SURFACE_TRANSFORM_SEED_${label}=[list $best_u $best_v] residual=$best_residual"
  bench_assert_close $best_residual 0.0 $tolerance "$label transformed support seed maps to the expected physical point"
  return [list $best_u $best_v]
}

proc bench_pcurve_samples {pcurve {fractions {0.2 0.5 0.8}}} {
  lassign [bench_curve_bounds $pcurve] t1 t2
  set samples {}
  foreach fraction $fractions {
    set parameter [expr {$t1+($t2-$t1)*$fraction}]
    uplevel #0 [list 2dcvalue $pcurve $parameter bench_pu bench_pv]
    set u [uplevel #0 {dval bench_pu}]
    set v [uplevel #0 {dval bench_pv}]
    if {![bench_is_finite $u] || ![bench_is_finite $v]} {
      return -code error "p-curve $pcurve has an unreadable sample at $parameter"
    }
    lappend samples [list $u $v]
  }
  return $samples
}

proc bench_surface_transform_uv_samples {source_surface transformed_surface uv_samples scale tx ty tz tolerance label} {
  set index 0
  foreach uv $uv_samples {
    lassign $uv u v
    bench_surface_transformed_uv $source_surface $transformed_surface $u $v \
      $scale $tx $ty $tz $tolerance "$label p-curve sample $index"
    incr index
  }
}

proc bench_pcurve_mapping_max {curve pcurve surface {samples 33}} {
  lassign [bench_curve_bounds $curve] c1 c2
  lassign [bench_curve_bounds $pcurve] p1 p2
  puts "BF_PARAMETER_RANGES_$curve=[list $c1 $c2]_$pcurve=[list $p1 $p2]"
  # BOP curves and their p-curves share the same parameter when they overlap.
  # Require explicit coverage, then sample the shared t values. Normalizing
  # two unrelated intervals would conceal a truncated or shifted p-curve.
  set range_scale [bench_max4 1.0 [expr {abs($c1)}] [expr {abs($c2)}] [bench_max [expr {abs($p1)}] [expr {abs($p2)}]]]
  set range_tol [expr {1.0e-10*$range_scale}]
  if {$p1 > $c1+$range_tol || $p2 < $c2-$range_tol} {
    return -code error "p-curve $pcurve parameter domain does not cover 3D curve $curve"
  }
  set max_residual 0.0
  for {set i 0} {$i < $samples} {incr i} {
    set tc [expr {$c1+($c2-$c1)*$i/double($samples-1)}]
    set tp $tc
    set xyz [bench_curve_point $curve $tc]
    uplevel #0 [list 2dcvalue $pcurve $tp bench_u bench_v]
    set u [uplevel #0 {dval bench_u}]
    set v [uplevel #0 {dval bench_v}]
    if {![bench_is_finite $u] || ![bench_is_finite $v]} {
      return -code error "non-finite or unreadable p-curve sample on $pcurve"
    }
    set mapped [bench_surface_xyz $surface $u $v]
    set residual [bench_distance3 $xyz $mapped]
    if {$residual > $max_residual} { set max_residual $residual }
  }
  return $max_residual
}

proc bench_curve_transform_max {curve baseline scale tx ty tz {samples 33}} {
  lassign [bench_curve_bounds $curve] c1 c2
  lassign [bench_curve_bounds $baseline] b1 b2
  set dense_samples [bench_max 401 [expr {20*$samples+1}]]
  set transformed_baseline {}
  for {set j 0} {$j < $dense_samples} {incr j} {
    set ratio [expr {double($j)/double($dense_samples-1)}]
    set source [bench_curve_point $baseline [expr {$b1+($b2-$b1)*$ratio}]]
    lassign $source bx by bz
    lappend transformed_baseline [list [expr {$scale*$bx+$tx}] [expr {$scale*$by+$ty}] [expr {$scale*$bz+$tz}]]
  }
  set current_samples {}
  for {set j 0} {$j < $dense_samples} {incr j} {
    set ratio [expr {double($j)/double($dense_samples-1)}]
    lappend current_samples [bench_curve_point $curve [expr {$c1+($c2-$c1)*$ratio}]]
  }
  set max_residual 0.0
  foreach point $current_samples {
    set nearest 1.0e100
    foreach reference $transformed_baseline {
      set distance [bench_distance3 $point $reference]
      if {$distance < $nearest} { set nearest $distance }
    }
    if {$nearest > $max_residual} { set max_residual $nearest }
  }
  foreach point $transformed_baseline {
    set nearest 1.0e100
    foreach reference $current_samples {
      set distance [bench_distance3 $point $reference]
      if {$distance < $nearest} { set nearest $distance }
    }
    if {$nearest > $max_residual} { set max_residual $nearest }
  }
  return $max_residual
}

proc bench_max {a b} {
  if {$a > $b} { return $a }
  return $b
}

proc bench_max4 {a b c d} {
  return [bench_max [bench_max $a $b] [bench_max $c $d]]
}

proc bench_max1 {a} {
  if {$a > 1.0} { return $a }
  return 1.0
}

proc bench_rename_curves {curves prefix} {
  set renamed {}
  foreach curve $curves {
    if {![regexp {_(\d+)$} $curve -> index]} { return -code error "cannot index curve $curve" }
    set target ${prefix}_$index
    uplevel #0 [list renamevar $curve $target]
    lappend renamed $target
  }
  return $renamed
}

proc bench_curve_transform_set {curves baselines scale tx ty tz tolerance {samples 33}} {
  if {[llength $curves] != [llength $baselines]} {
    bench_assert {0} "transformed geometry preserves baseline branch count"
    return
  }
  set available $baselines
  foreach curve $curves {
    set best_index -1
    set best_residual 1.0e100
    for {set i 0} {$i < [llength $available]} {incr i} {
      set residual [bench_curve_transform_max $curve [lindex $available $i] $scale $tx $ty $tz $samples]
      if {$residual < $best_residual} { set best_residual $residual; set best_index $i }
    }
    if {$best_index < 0} {
      bench_assert {0} "$curve has a matching transformed baseline branch"
      continue
    }
    bench_assert_close $best_residual 0.0 $tolerance "$curve coordinates equal the transformed baseline samples"
    set available [lreplace $available $best_index $best_index]
  }
}

proc bench_intersection_support_mapping {root curves surface1 surface2 tolerance {samples 33}} {
  foreach curve $curves {
    if {![regexp {_(\d+)$} $curve -> index]} {
      return -code error "cannot map intersection branch $curve to its p-curves"
    }
    set pcurve1 ${root}2d1_$index
    set pcurve2 ${root}2d2_$index
    set residual1 [bench_pcurve_mapping_max $curve $pcurve1 $surface1 $samples]
    set residual2 [bench_pcurve_mapping_max $curve $pcurve2 $surface2 $samples]
    puts "BF_SUPPORT_MAPPING_MAX_RESIDUAL_${index}_1=$residual1"
    puts "BF_SUPPORT_MAPPING_MAX_RESIDUAL_${index}_2=$residual2"
    bench_assert_close $residual1 0.0 $tolerance "$curve maps through its first p-curve to the first support"
    bench_assert_close $residual2 0.0 $tolerance "$curve maps through its second p-curve to the second support"
  }
}

proc bench_cone_sphere_case {prefix sphere_radius scale tx ty tz} {
  set cone_radius [expr {15.0*$scale}]
  set cone_height [expr {10.0*$scale}]
  set sphere_radius [expr {$sphere_radius*$scale}]
  set linear_tol [expr {1.0e-4*[bench_max1 $scale]}]
  uplevel #0 [list pcone ${prefix}_cone $cone_radius 0.0 $cone_height]
  uplevel #0 [list psphere ${prefix}_sphere $sphere_radius]
  uplevel #0 [list ttranslate ${prefix}_cone $tx $ty $tz]
  uplevel #0 [list ttranslate ${prefix}_sphere $tx $ty $tz]
  uplevel #0 [list explode ${prefix}_cone f]
  uplevel #0 [list explode ${prefix}_sphere f]
  uplevel #0 [list mksurface ${prefix}_cone_surface ${prefix}_cone_1]
  uplevel #0 [list mksurface ${prefix}_sphere_surface ${prefix}_sphere_1]
  uplevel #0 [list intersect ${prefix}_result ${prefix}_cone_surface ${prefix}_sphere_surface]
  if {[string first "3d curve" [uplevel #0 [list whatis ${prefix}_result]]] >= 0} {
    uplevel #0 [list renamevar ${prefix}_result ${prefix}_result_1]
  }
  set curves [bench_curve_names ${prefix}_result]
  bench_assert {[llength $curves] == 2} "$prefix has two intersection curves"
  set isolated_points 0
  for {set i 1} {$i <= 16} {incr i} {
    if {[uplevel #0 [list info exists ${prefix}_result_p_$i]]} { incr isolated_points }
  }
  bench_assert {$isolated_points == 0} "$prefix has no isolated intersection points"

  set aa [expr {($cone_radius/$cone_height)**2+1.0}]
  set bb [expr {-2.0*$cone_radius*$cone_radius/$cone_height}]
  set cc [expr {$cone_radius*$cone_radius-$sphere_radius*$sphere_radius}]
  set discriminant [expr {$bb*$bb-4.0*$aa*$cc}]
  bench_assert {$discriminant > 0.0} "$prefix analytic roots are distinct and real"
  if {$discriminant < 0.0} { set discriminant 0.0 }
  set root_delta [expr {sqrt($discriminant)}]
  set roots [list [expr {(-$bb-$root_delta)/(2.0*$aa)}] [expr {(-$bb+$root_delta)/(2.0*$aa)}]]
  set assigned {}
  foreach curve $curves {
    lassign [bench_curve_bounds $curve] u1 u2
    set midpoint [bench_curve_point $curve [expr {($u1+$u2)/2.0}]]
    set local_mid_z [expr {[lindex $midpoint 2]-$tz}]
    set root_index 0
    set best_index -1
    set best_error 1.0e100
    foreach root $roots {
      set error [expr {abs($local_mid_z-$root)}]
      if {$error < $best_error} { set best_error $error; set best_index $root_index }
      incr root_index
    }
    bench_assert {[lsearch -exact $assigned $best_index] < 0} "$prefix curves map to distinct analytic roots"
    lappend assigned $best_index
    bench_assert_close $best_error 0.0 $linear_tol "$prefix $curve assigned-root residual"
    set gap [bench_closed_curve_gap $curve]
    bench_assert_close $gap 0.0 $linear_tol "$prefix $curve is closed"
    for {set i 0} {$i <= 16} {incr i} {
      set parameter [expr {$u1+($u2-$u1)*$i/16.0}]
      lassign [bench_curve_point $curve $parameter] x y z
      set lx [expr {$x-$tx}]
      set ly [expr {$y-$ty}]
      set lz [expr {$z-$tz}]
      set rho [expr {sqrt($lx*$lx+$ly*$ly)}]
      set cone_residual [expr {abs($rho-$cone_radius*(1.0-$lz/$cone_height))}]
      set sphere_residual [expr {abs(sqrt($rho*$rho+$lz*$lz)-$sphere_radius)}]
      bench_assert_close $cone_residual 0.0 $linear_tol "$prefix $curve sample $i cone support residual"
      bench_assert_close $sphere_residual 0.0 $linear_tol "$prefix $curve sample $i sphere support residual"
    }
  }
  bench_assert {[lsort -integer $assigned] eq {0 1}} "$prefix covers both analytic roots"
}

proc bench_cone_plane_ring_case {prefix scale plane_height} {
  set radius [expr {15.0*$scale}]
  set height [expr {10.0*$scale}]
  set z [expr {$plane_height*$scale}]
  set expected_radius [expr {$radius*(1.0-$z/$height)}]
  set tol [expr {1.0e-4*[bench_max1 $scale]}]
  uplevel #0 [list pcone ${prefix}_cone $radius 0.0 $height]
  uplevel #0 [list explode ${prefix}_cone f]
  uplevel #0 [list mksurface ${prefix}_cone_surface ${prefix}_cone_1]
  uplevel #0 [list plane ${prefix}_plane 0.0 0.0 $z 0.0 0.0 1.0]
  uplevel #0 [list intersect ${prefix}_result ${prefix}_cone_surface ${prefix}_plane]
  if {[string first "3d curve" [uplevel #0 [list whatis ${prefix}_result]] ] >= 0} {
    uplevel #0 [list renamevar ${prefix}_result ${prefix}_result_1]
  }
  set curves [bench_curve_names ${prefix}_result]
  bench_assert {[llength $curves] == 1} "$prefix has one cone/plane ring"
  foreach curve $curves {
    bench_assert_close [bench_closed_curve_gap $curve] 0.0 $tol "$prefix ring closes"
    lassign [bench_curve_bounds $curve] u1 u2
    for {set i 0} {$i <= 16} {incr i} {
      set point [bench_curve_point $curve [expr {$u1+($u2-$u1)*$i/16.0}]]
      lassign $point x y sample_z
      set rho [expr {sqrt($x*$x+$y*$y)}]
      bench_assert_close $sample_z $z $tol "$prefix sample $i lies on plane"
      bench_assert_close $rho $expected_radius $tol "$prefix sample $i has analytic cone radius"
    }
  }
}

proc bench_volume {shape} {
  set report [uplevel #0 [list vprops $shape]]
  if {![regexp -nocase {Mass[[:space:]]*:[[:space:]]*([-+0-9.eE]+)} $report -> value]} {
    return -code error "could not parse volume from vprops $shape: $report"
  }
  return $value
}

proc bench_centered_three_cylinder_common {prefix radius} {
  set length [expr {4.0*$radius}]
  set tx [expr {3.0*$radius}]
  set ty [expr {-1.25*$radius}]
  set tz [expr {0.5*$radius}]
  uplevel #0 [list plane ${prefix}_px [expr {-2.0*$radius+$tx}] $ty $tz 1 0 0]
  uplevel #0 [list plane ${prefix}_py $tx [expr {-2.0*$radius+$ty}] $tz 0 1 0]
  uplevel #0 [list plane ${prefix}_pz $tx $ty [expr {-2.0*$radius+$tz}] 0 0 1]
  uplevel #0 [list pcylinder ${prefix}_cx ${prefix}_px $radius $length]
  uplevel #0 [list pcylinder ${prefix}_cy ${prefix}_py $radius $length]
  uplevel #0 [list pcylinder ${prefix}_cz ${prefix}_pz $radius $length]
  uplevel #0 [list bcommon ${prefix}_pair ${prefix}_cx ${prefix}_cy]
  uplevel #0 [list bcommon ${prefix}_common ${prefix}_pair ${prefix}_cz]
  set shape_rc [catch {uplevel #0 [list checkshape ${prefix}_common]} shape_audit]
  set bop_rc [catch {uplevel #0 [list bopcheck ${prefix}_common]} bop_audit]
  bench_assert {$shape_rc == 0 && [regexp -nocase {seems to be valid|looks OK} $shape_audit]} "$prefix common shape is valid"
  bench_assert {$bop_rc == 0 && [regexp -nocase {seems to be OK|looks OK} $bop_audit]} "$prefix common shape passes BOP check"
  uplevel #0 [list explode ${prefix}_common sol]
  set solid_count 0
  for {set i 1} {$i <= 16} {incr i} {
    if {[catch {uplevel #0 [list whatis ${prefix}_common_$i]} solid_type] || ![regexp -nocase {shape SOLID} $solid_type]} { break }
    incr solid_count
  }
  bench_assert {$solid_count == 1} "$prefix common result has one solid"
  set expected [expr {8.0*(2.0-sqrt(2.0))*$radius**3}]
  set tolerance [expr {2.0e-4*$expected}]
  bench_assert_close [bench_volume ${prefix}_common] $expected $tolerance \
    "$prefix common volume matches analytic three-cylinder intersection"
}

proc bench_brep_27252_case {prefix input scale plane_offset} {
  set offset [expr {$plane_offset*$scale}]
  uplevel #0 [list restore $input ${prefix}_base]
  uplevel #0 [list explode ${prefix}_base]
  uplevel #0 [list mkplane ${prefix}_base_f ${prefix}_base_2]
  uplevel #0 [list prism ${prefix}_base_prism ${prefix}_base_f -25.0 0 0]
  uplevel #0 [list explode ${prefix}_base_1 f]
  uplevel #0 [list explode ${prefix}_base_prism f]
  uplevel #0 [list ttranslate ${prefix}_base_prism_3 0 0 $plane_offset]
  set baseline_log [uplevel #0 [list bopcurves ${prefix}_base_1_7 ${prefix}_base_prism_3 -2d]]
  set baseline_curves [bench_curve_names c]
  bench_assert {[llength $baseline_curves] == 1} "$prefix unscaled BREP baseline has one intersection curve"
  set baseline_curves [bench_rename_curves $baseline_curves ${prefix}_baseline_curve]
  puts "BF_BASELINE_BOPCURVES_LOG_BEGIN_$prefix"
  puts $baseline_log
  puts "BF_BASELINE_BOPCURVES_LOG_END_$prefix"

  uplevel #0 [list restore $input ${prefix}_a]
  if {$scale != 1.0} { uplevel #0 [list tscale ${prefix}_a 0 0 0 $scale] }
  uplevel #0 [list explode ${prefix}_a]
  uplevel #0 [list mkplane ${prefix}_f ${prefix}_a_2]
  uplevel #0 [list prism ${prefix}_p ${prefix}_f [expr {-25.0*$scale}] 0 0]
  uplevel #0 [list explode ${prefix}_a_1 f]
  uplevel #0 [list explode ${prefix}_p f]
  uplevel #0 [list ttranslate ${prefix}_p_3 0 0 $offset]
  set log [uplevel #0 [list bopcurves ${prefix}_a_1_7 ${prefix}_p_3 -2d]]
  set curves [bench_curve_names c]
  bench_assert {[llength $curves] == 1} "$prefix BREP intersection has one curve"
  bench_curve_transform_set $curves $baseline_curves $scale 0.0 0.0 0.0 \
    [expr {1.0e-4*[bench_max1 $scale]}] 101
  puts "BF_BOPCURVES_LOG_BEGIN_$prefix"
  puts $log
  puts "BF_BOPCURVES_LOG_END_$prefix"
  uplevel #0 [list mksurface ${prefix}_surface_a ${prefix}_a_1_7]
  uplevel #0 [list mksurface ${prefix}_surface_p ${prefix}_p_3]
  set tolerance [expr {1.0e-4*[bench_max1 $scale]}]
  bench_intersection_support_mapping c $curves ${prefix}_surface_a ${prefix}_surface_p $tolerance 101
}

proc bench_m27780_case {prefix input_a input_b scale relative_dx tx ty tz} {
  set seed_u1 6.2406621764215551
  set seed_v1 0.23999999463558200
  set seed_u2 0.00034444887595448459
  set seed_v2 -5.0019657458625186

  uplevel #0 [list restore $input_a ${prefix}_base_p]
  uplevel #0 [list restore $input_b ${prefix}_base_t]
  uplevel #0 [list ttranslate ${prefix}_base_t $relative_dx 0 0]
  uplevel #0 [list mksurface ${prefix}_base_surface_p ${prefix}_base_p]
  uplevel #0 [list explode ${prefix}_base_t f]
  uplevel #0 [list mksurface ${prefix}_base_surface_t ${prefix}_base_t_2]
  set base_seed_point1 [bench_surface_xyz ${prefix}_base_surface_p $seed_u1 $seed_v1]
  set base_seed_point2 [bench_surface_xyz ${prefix}_base_surface_t $seed_u2 $seed_v2]
  set base_seed_separation [bench_distance3 $base_seed_point1 $base_seed_point2]
  puts "BF_BASE_SEED_SUPPORT_SEPARATION_$prefix=$base_seed_separation"
  bench_assert_close $base_seed_separation [expr {abs($relative_dx)}] 1.0e-5 \
    "$prefix original UV seed separation matches the intentional face translation"
  set base_log [uplevel #0 [list bopcurves ${prefix}_base_p ${prefix}_base_t_2 -2d \
    -p $seed_u1 $seed_v1 $seed_u2 $seed_v2]]
  set base_curves [bench_curve_names c]
  bench_assert {[llength $base_curves] == 1} "$prefix baseline has one seed-selected branch"
  set base_seed_distance [bench_curve_distance_min [lindex $base_curves 0] $base_seed_point1 257]
  set base_seed_distance2 [bench_curve_distance_min [lindex $base_curves 0] $base_seed_point2 257]
  puts "BF_BASE_SEED_TO_CURVE_RESIDUALS_$prefix=[list $base_seed_distance $base_seed_distance2]"
  set base_curves [bench_rename_curves $base_curves ${prefix}_base_curve]
  puts "BF_BASE_BOPCURVES_LOG_BEGIN_$prefix"
  puts $base_log
  puts "BF_BASE_BOPCURVES_LOG_END_$prefix"

  uplevel #0 [list restore $input_a ${prefix}_p]
  uplevel #0 [list restore $input_b ${prefix}_t]
  uplevel #0 [list ttranslate ${prefix}_t $relative_dx 0 0]
  if {$scale != 1.0} {
    uplevel #0 [list tscale ${prefix}_p 0 0 0 $scale]
    uplevel #0 [list tscale ${prefix}_t 0 0 0 $scale]
  }
  uplevel #0 [list ttranslate ${prefix}_p $tx $ty $tz]
  uplevel #0 [list ttranslate ${prefix}_t $tx $ty $tz]
  uplevel #0 [list mksurface ${prefix}_surface_p ${prefix}_p]
  uplevel #0 [list explode ${prefix}_t f]
  uplevel #0 [list mksurface ${prefix}_surface_t ${prefix}_t_2]
  set uv1 [bench_surface_transformed_uv ${prefix}_base_surface_p ${prefix}_surface_p \
    $seed_u1 $seed_v1 $scale $tx $ty $tz [expr {1.0e-6*[bench_max1 $scale]}] "$prefix first face"]
  set uv2 [bench_surface_transformed_uv ${prefix}_base_surface_t ${prefix}_surface_t \
    $seed_u2 $seed_v2 $scale $tx $ty $tz [expr {1.0e-6*[bench_max1 $scale]}] "$prefix second face"]
  lassign $uv1 seed_u1_transformed seed_v1_transformed
  lassign $uv2 seed_u2_transformed seed_v2_transformed
  set transformed_seed_point1 [bench_surface_xyz ${prefix}_surface_p $seed_u1_transformed $seed_v1_transformed]
  set transformed_seed_point2 [bench_surface_xyz ${prefix}_surface_t $seed_u2_transformed $seed_v2_transformed]
  set transformed_seed_separation [bench_distance3 $transformed_seed_point1 $transformed_seed_point2]
  puts "BF_TRANSFORMED_SEED_SUPPORT_SEPARATION_$prefix=$transformed_seed_separation"
  bench_assert_close $transformed_seed_separation [expr {$scale*$base_seed_separation}] \
    [expr {1.0e-6*[bench_max1 $scale]}] \
    "$prefix transformed UV seed separation matches the scaled BRep offset"
  set log [uplevel #0 [list bopcurves ${prefix}_p ${prefix}_t_2 -2d \
    -p $seed_u1_transformed $seed_v1_transformed $seed_u2_transformed $seed_v2_transformed]]
  set curves [bench_curve_names c]
  bench_assert {[llength $curves] == 1} "$prefix has one selected 3D intersection branch"
  set selected_seed_distance [bench_curve_distance_min [lindex $curves 0] $transformed_seed_point1 257]
  set selected_seed_distance2 [bench_curve_distance_min [lindex $curves 0] $transformed_seed_point2 257]
  puts "BF_SELECTED_SEED_TO_CURVE_RESIDUALS_$prefix=[list $selected_seed_distance $selected_seed_distance2]"
  bench_assert_close $selected_seed_distance [expr {$scale*$base_seed_distance}] \
    [expr {1.0e-5*[bench_max1 $scale]}] \
    "$prefix selected 3D branch retains its first UV-seed distance under scale"
  bench_assert_close $selected_seed_distance2 [expr {$scale*$base_seed_distance2}] \
    [expr {1.0e-5*[bench_max1 $scale]}] \
    "$prefix selected 3D branch retains its second UV-seed distance under scale"
  puts "BF_BOPCURVES_LOG_BEGIN_$prefix"
  puts $log
  puts "BF_BOPCURVES_LOG_END_$prefix"
  if {$scale == 1.0} {
    bench_curve_transform_set $curves $base_curves $scale $tx $ty $tz \
      [expr {1.0e-5*[bench_max1 $scale]}] 33
  }
  set tolerance [expr {1.0e-5*[bench_max1 $scale]}]
  foreach curve $curves {
    if {![regexp {_(\d+)$} $curve -> index]} { error "cannot map intersection branch name $curve to its p-curves" }
    set pc1 c2d1_$index
    set pc2 c2d2_$index
    set residual1 [bench_pcurve_mapping_max $curve $pc1 ${prefix}_surface_p 33]
    set residual2 [bench_pcurve_mapping_max $curve $pc2 ${prefix}_surface_t 33]
    puts "BF_PCURVE_SUPPORT_RESIDUAL_1_$index=$residual1"
    puts "BF_PCURVE_SUPPORT_RESIDUAL_2_$index=$residual2"
    bench_assert_close $residual1 0.0 $tolerance "$prefix branch $index 3D/p-curve/support residual on first face"
    bench_assert_close $residual2 0.0 $tolerance "$prefix branch $index 3D/p-curve/support residual on second face"
    uplevel #0 [list trim ${prefix}_trim_$index $pc1 0 1]
    uplevel #0 [list 2dcvalue ${prefix}_trim_$index 0 ${prefix}_u0 ${prefix}_v0]
    uplevel #0 [list 2dcvalue ${prefix}_trim_$index 1 ${prefix}_u1 ${prefix}_v1 ${prefix}_du ${prefix}_dv]
    foreach name {u0 v0 u1 v1 du dv} { set ${prefix}_$name [uplevel #0 [list dval ${prefix}_$name]] }
    set u0 [set ${prefix}_u0]; set v0 [set ${prefix}_v0]
    set u1 [set ${prefix}_u1]; set v1 [set ${prefix}_v1]
    set du [set ${prefix}_du]; set dv [set ${prefix}_dv]
    set direction_dot [expr {($u1-$u0)*$du+($v1-$v0)*$dv}]
    puts "BF_PCURVE_ENDPOINT_DIRECTION_DOT_$index=$direction_dot"
    bench_assert {$direction_dot > 0.0} "$prefix branch $index endpoint p-curve direction agrees with increasing parameter"
  }
}
