# Shared support for the added five-group neighborhood checkpoints.
# The public issue scripts remain byte-for-byte inputs; only their embedded
# BREP fixture assignments are read here.

set ::mn_bundle_root [file dirname [file normalize [info script]]]
while {![file isdirectory [file join $::mn_bundle_root issues]]} {
  set ::mn_parent [file dirname $::mn_bundle_root]
  if {$::mn_parent eq $::mn_bundle_root} {
    error "cannot locate frozen benchmark bundle root"
  }
  set ::mn_bundle_root $::mn_parent
}

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

proc bench_assert_close {actual expected tolerance label} {
  foreach value [list $actual $expected $tolerance] {
    if {![string is double -strict $value] ||
        [catch {expr {abs(double($value)) <= 1.7976931348623157e308}} finite] ||
        !$finite} {
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

proc bench_assert_range {actual lower upper label} {
  foreach value [list $actual $lower $upper] {
    if {![string is double -strict $value] ||
        [catch {expr {abs(double($value)) <= 1.7976931348623157e308}} finite] ||
        !$finite} {
      return [::bench::_record numeric 0 $label \
        "actual=$actual lower=$lower upper=$upper non_finite_or_non_numeric"]
    }
  }
  set passed [expr {double($lower) <= double($actual) && double($actual) <= double($upper)}]
  return [::bench::_record numeric $passed $label "actual=$actual lower=$lower upper=$upper"]
}

proc bench_finish {} {
  variable ::bench::assertions
  variable ::bench::numeric_assertions
  variable ::bench::failures
  if {$assertions < 1} { error "bench_finish requires at least one assertion" }
  if {$failures != 0} {
    puts stderr "BENCH_ORACLE_FAILED assertions=$assertions failures=$failures"
    error "one or more benchmark assertions failed"
  }
  puts "BENCH_ORACLE_OK assertions=$assertions numeric_assertions=$numeric_assertions"
  puts "TEST_DONE assertions=$assertions numeric_assertions=$numeric_assertions"
}

proc mn_load_fixture {issue_id issue_version} {
  set path [file join $::mn_bundle_root issues $issue_id $issue_version public original.tcl]
  if {![file isfile $path] && [string match mantis-* $issue_id]} {
    set local_issue_id [string map {mantis- occt-} $issue_id]
    set path [file join $::mn_bundle_root issues $local_issue_id $issue_version public original.tcl]
  }
  if {![file isfile $path]} { error "missing frozen public input: $path" }
  set channel [open $path r]
  set loaded 0
  while {[gets $channel line] >= 0} {
    if {[regexp {^set ::([[:alnum:]_]+_brep) \{([A-Za-z0-9+/=]+)\}$} $line -> name payload]} {
      set ::$name $payload
      incr loaded
    }
  }
  close $channel
  if {$loaded == 0} { error "no embedded BREP fixtures found in $path" }
  puts "MN_FIXTURES_LOADED issue=$issue_id version=$issue_version count=$loaded"
}

proc mn_restore_b64 {encoded shape key} {
  set scratch [pwd]
  if {[info exists ::env(TMPDIR)] && $::env(TMPDIR) ne ""} { set scratch $::env(TMPDIR) }
  set path [file join $scratch [format ".occt_%s_%d.brep" $key [pid]]]
  set f [open $path wb]
  fconfigure $f -translation binary -encoding binary
  puts -nonewline $f [binary decode base64 $encoded]
  close $f
  uplevel #0 [list restore $path $shape]
  file delete -force $path
}

proc mn_curve_count {root} {
  set n 0
  for {set i 1} {$i <= 64} {incr i} {
    set name ${root}_$i
    if {[catch {uplevel #0 [list whatis $name]} type] ||
        [string first "3d curve" $type] < 0} { break }
    incr n
  }
  return $n
}

proc mn_retain_curves {root prefix count} {
  for {set i 1} {$i <= $count} {incr i} {
    uplevel #0 [list renamevar ${root}_$i ${prefix}_$i]
  }
}

proc mn_report_intersection {report expected label} {
  if {![regexp {Tolerance Reached=+([-0-9.+eE]+)\n+([-0-9.+eE]+)} $report -> tol count]} {
    bench_assert {0} "$label reports a measurable intersection"
    return -1
  }
  set found [mn_curve_count c]
  set ::mn_last_reported_tolerance $tol
  bench_assert {$found == $expected} "$label 3D branch count"
  bench_assert {$count == $expected} "$label reported branch count"
  bench_assert_range $tol 0 1.0e100 "$label reported tolerance is finite and nonnegative"
  return $found
}

# xdistcs returns its per-sample point-to-surface distances and a final maximum.
# The projection command initializes GeomAPI_ProjectPointOnSurf with 1e-7 in
# OCCT; preserve the measured maximum instead of relying on its diagnostic text.
proc mn_physical_residual_max {curve surface samples label} {
  uplevel #0 [list bounds $curve mn_u1 mn_u2]
  set u1 [uplevel #0 {dval mn_u1}]
  set u2 [uplevel #0 {dval mn_u2}]
  if {![string is double -strict $u1] || ![string is double -strict $u2] || $u2 <= $u1} {
    bench_assert {0} "$label curve bounds are measurable"
    return -1.0
  }
  # A high reporting threshold keeps xdistcs output parseable without making
  # its internal error/warning classification the oracle. The numeric maximum
  # is compared by the caller against the independently reported BOP tolerance.
  set report [uplevel #0 [list xdistcs $curve $surface $u1 $u2 $samples 1.0e100]]
  if {[info exists ::env(MANTIS_NEIGHBOR_LOG_DIR)] && $::env(MANTIS_NEIGHBOR_LOG_DIR) ne ""} {
    file mkdir $::env(MANTIS_NEIGHBOR_LOG_DIR)
    if {![info exists ::mn_xdistcs_log_index]} { set ::mn_xdistcs_log_index 0 }
    incr ::mn_xdistcs_log_index
    set raw_path [file join $::env(MANTIS_NEIGHBOR_LOG_DIR) \
      [format "xdistcs-%03d.txt" $::mn_xdistcs_log_index]]
    set raw_file [open $raw_path w]
    puts $raw_file "case=$label curve=$curve surface=$surface samples=$samples parameter_bounds=$u1,$u2"
    puts -nonewline $raw_file $report
    close $raw_file
    puts "MN_XDISTCS_LOG label=[list $label] path=$raw_path"
  }
  if {![regexp {Max distance = +([-+0-9.eE]+)} $report -> maximum] ||
      ![string is double -strict $maximum] ||
      [catch {expr {double($maximum) >= 0.0 && abs(double($maximum)) <= 1.7976931348623157e308}} valid] ||
      !$valid} {
    bench_assert {0} "$label sampled physical maximum is measurable"
    return -1.0
  }
  set max_param unknown
  regexp {Param = +([-+0-9.eE]+)} $report -> max_param
  puts "MN_PHYSICAL_MAX label=[list $label] samples=$samples max_distance=$maximum max_param=$max_param"
  return $maximum
}

proc mn_absolute_physical_upper {scale} {
  # 6.5e-7 is the issue's source-model linear precision budget. Uniformly
  # scaling the geometry scales that allowance; xdistcs contributes its own
  # 1e-7 projection tolerance in world units.
  return [expr {6.5e-7*abs(double($scale)) + 1.0e-7*max(1.0,abs(double($scale)))}]
}

proc mn_assert_absolute_cap_independent_of_reported_tolerance {scale label} {
  set physical_upper [mn_absolute_physical_upper $scale]
  set prior_tolerance $::mn_last_reported_tolerance
  set ::mn_last_reported_tolerance 1.0e6
  set inflated_reported_upper [mn_absolute_physical_upper $scale]
  set ::mn_last_reported_tolerance $prior_tolerance
  puts "MN_ABSOLUTE_CAP_NEGATIVE_CONTROL label=[list $label] synthetic_reported_tol=1.0e6 physical_upper=$physical_upper recomputed_upper=$inflated_reported_upper"
  bench_assert_close $inflated_reported_upper $physical_upper 0.0 \
    "$label physical cap does not expand when a synthetic reported tolerance is inflated"
}

proc mn_check_residual_with_reported_tolerance {curve surface scale label} {
  set coarse [mn_physical_residual_max $curve $surface 20 "$label coarse20"]
  set maximum [mn_physical_residual_max $curve $surface 1000 "$label dense1000"]
  if {$maximum < 0.0 || ![info exists ::mn_last_reported_tolerance]} { return }
  if {$coarse >= 0.0} {
    puts "MN_SAMPLING_COMPARISON label=[list $label] samples20_max=$coarse samples1000_max=$maximum"
  }
  # Trusted NG04/NG05 maxima are 1.0316072452158535e-7 at scale 0.5 and
  # 2.6042148265552454e-7 at scale 2.0, both below this issue-budget cap.
  # The cap comes from source precision, not from mutable intersection output.
  set projection_slack [expr {1.0e-7 * max(1.0, abs(double($scale)))}]
  set absolute_upper [mn_absolute_physical_upper $scale]
  puts "MN_PHYSICAL_ABSOLUTE_BOUND label=[list $label] source_precision_budget=[expr {6.5e-7*abs(double($scale))}] projection_slack=$projection_slack upper=$absolute_upper scale=$scale"
  bench_assert_range $maximum 0.0 $absolute_upper \
    "$label physical residual is within trusted reference envelope, independent of reported tolerance"

  # Keep the separate self-consistency check too: an intersection routine
  # cannot report a tolerance below the measured geometry residual.
  set numerical_margin [expr {1.0e-7 * max(1.0, abs(double($scale)))}]
  set upper [expr {double($::mn_last_reported_tolerance) + $numerical_margin}]
  puts "MN_PHYSICAL_BOUND label=[list $label] reported_tol=$::mn_last_reported_tolerance numerical_margin=$numerical_margin upper=$upper scale=$scale"
  bench_assert_range $maximum 0.0 $upper "$label physical residual <= reported tolerance + projection margin"
}

proc mn_shape_valid {shape label} {
  set audit [uplevel #0 [list bopcheck $shape]]
  bench_assert {[regexp -nocase {OK} $audit]} "$label BOP validity"
  set report [uplevel #0 [list checkshape $shape]]
  bench_assert {[regexp -nocase {valid} $report] && ![regexp -nocase {faulty|invalid} $report]} \
    "$label topological validity"
}

proc mn_shape_volume {shape} {
  set report [uplevel #0 [list vprops $shape]]
  if {![regexp -nocase {Mass[[:space:]]*:[[:space:]]*([-+0-9.eE]+)} $report -> value] ||
      ![string is double -strict $value]} {
    return -code error "cannot parse volume for $shape: $report"
  }
  return $value
}

proc mn_curve_length {curve} {
  set report [uplevel #0 [list length $curve]]
  if {![regexp {is[[:space:]]+([-+0-9.eE]+)} $report -> value] ||
      ![string is double -strict $value]} {
    return -code error "cannot parse curve length for $curve: $report"
  }
  return $value
}

proc mn_surface_xyz {surface u v} {
  uplevel #0 [list svalue $surface $u $v mn_sx mn_sy mn_sz]
  set point [list [uplevel #0 {dval mn_sx}] [uplevel #0 {dval mn_sy}] [uplevel #0 {dval mn_sz}]]
  foreach value $point {
    if {![string is double -strict $value]} {
      return -code error "cannot read point from $surface at ($u,$v)"
    }
  }
  return $point
}

proc mn_transform_point {point scale angle dx dy dz} {
  lassign $point x y z
  set norm [expr {sqrt(14.0)}]
  set ux [expr {1.0/$norm}]
  set uy [expr {2.0/$norm}]
  set uz [expr {3.0/$norm}]
  set radians [expr {double($angle)*acos(-1.0)/180.0}]
  set cosine [expr {cos($radians)}]
  set sine [expr {sin($radians)}]
  set dot [expr {$ux*$x+$uy*$y+$uz*$z}]
  set cx [expr {$uy*$z-$uz*$y}]
  set cy [expr {$uz*$x-$ux*$z}]
  set cz [expr {$ux*$y-$uy*$x}]
  set rx [expr {$x*$cosine+$cx*$sine+$ux*$dot*(1.0-$cosine)}]
  set ry [expr {$y*$cosine+$cy*$sine+$uy*$dot*(1.0-$cosine)}]
  set rz [expr {$z*$cosine+$cz*$sine+$uz*$dot*(1.0-$cosine)}]
  return [list [expr {$rx*$scale+$dx}] [expr {$ry*$scale+$dy}] [expr {$rz*$scale+$dz}]]
}

proc mn_assert_transformed_surface_point {source_surface transformed_surface u v scale angle dx dy dz label} {
  if {[catch {mn_surface_xyz $source_surface $u $v} source_point] ||
      [catch {mn_surface_xyz $transformed_surface $u $v} actual_point]} {
    bench_assert {0} "$label source and transformed sample points are measurable"
    return
  }
  set expected [mn_transform_point $source_point $scale $angle $dx $dy $dz]
  lassign $expected ex ey ez
  lassign $actual_point ax ay az
  set error [expr {sqrt(($ax-$ex)**2+($ay-$ey)**2+($az-$ez)**2)}]
  set tolerance [expr {1.0e-8*max(1.0,abs($dx),abs($dy),abs($dz),abs($scale))}]
  puts "MN_TRANSFORM_WITNESS label=[list $label] source=$source_point expected=$expected actual=$actual_point error=$error tolerance=$tolerance"
  bench_assert_range $error 0.0 $tolerance "$label sampled coordinates prove scale/rotation/translation"
}

proc mn_assert_transformed_surface_midpoint {source_surface transformed_surface scale angle dx dy dz label} {
  if {[catch {uplevel #0 [list bounds $source_surface mn_bound_u1 mn_bound_u2 mn_bound_v1 mn_bound_v2]}]} {
    bench_assert {0} "$label source surface bounds are measurable"
    return
  }
  set u1 [uplevel #0 {dval mn_bound_u1}]
  set u2 [uplevel #0 {dval mn_bound_u2}]
  set v1 [uplevel #0 {dval mn_bound_v1}]
  set v2 [uplevel #0 {dval mn_bound_v2}]
  foreach value [list $u1 $u2 $v1 $v2] {
    if {![string is double -strict $value] || abs(double($value)) >= 1.0e50} {
      set u1 0.2; set u2 0.2; set v1 0.3; set v2 0.3
      break
    }
  }
  set u [expr {($u1+$u2)/2.0}]
  set v [expr {($v1+$v2)/2.0}]
  puts "MN_TRANSFORM_SAMPLE label=[list $label] source_bounds={$u1,$u2,$v1,$v2} parameter={$u,$v}"
  mn_assert_transformed_surface_point $source_surface $transformed_surface $u $v \
    $scale $angle $dx $dy $dz $label
}

proc mn_curve_point {curve parameter} {
  uplevel #0 [list cvalue $curve $parameter mn_cx mn_cy mn_cz mn_cdx mn_cdy mn_cdz]
  set point [list [uplevel #0 {dval mn_cx}] [uplevel #0 {dval mn_cy}] [uplevel #0 {dval mn_cz}]]
  foreach value $point {
    if {![string is double -strict $value]} {
      return -code error "cannot read curve point from $curve at $parameter"
    }
  }
  return $point
}

proc mn_curve_sample_points {curve samples} {
  uplevel #0 [list bounds $curve mn_curve_sample_u1 mn_curve_sample_u2]
  set u1 [uplevel #0 {dval mn_curve_sample_u1}]
  set u2 [uplevel #0 {dval mn_curve_sample_u2}]
  if {![string is double -strict $u1] || ![string is double -strict $u2] ||
      $u2 <= $u1 || $samples < 2} {
    return -code error "cannot sample $curve over [$u1,$u2]"
  }
  set points {}
  for {set i 0} {$i < $samples} {incr i} {
    set parameter [expr {$u1+($u2-$u1)*$i/double($samples-1)}]
    lappend points [mn_curve_point $curve $parameter]
  }
  return $points
}

proc mn_point_distance {point_a point_b} {
  lassign $point_a ax ay az
  lassign $point_b bx by bz
  return [expr {sqrt(($ax-$bx)**2+($ay-$by)**2+($az-$bz)**2)}]
}

proc mn_curve_directed_sample_distance {points_a points_b} {
  set maximum 0.0
  foreach point_a $points_a {
    set nearest 1.0e100
    foreach point_b $points_b {
      set distance [mn_point_distance $point_a $point_b]
      if {$distance < $nearest} { set nearest $distance }
    }
    if {$nearest > $maximum} { set maximum $nearest }
  }
  return $maximum
}

proc mn_curve_sample_hausdorff {curve_a curve_b samples} {
  set points_a [mn_curve_sample_points $curve_a $samples]
  set points_b [mn_curve_sample_points $curve_b $samples]
  return [expr {max([mn_curve_directed_sample_distance $points_a $points_b], \
                    [mn_curve_directed_sample_distance $points_b $points_a])}]
}

proc mn_inverse_transform_point {point scale angle dx dy dz} {
  lassign $point x y z
  set x [expr {$x-$dx}]
  set y [expr {$y-$dy}]
  set z [expr {$z-$dz}]
  set norm [expr {sqrt(14.0)}]
  set ux [expr {1.0/$norm}]
  set uy [expr {2.0/$norm}]
  set uz [expr {3.0/$norm}]
  set radians [expr {-double($angle)*acos(-1.0)/180.0}]
  set cosine [expr {cos($radians)}]
  set sine [expr {sin($radians)}]
  set dot [expr {$ux*$x+$uy*$y+$uz*$z}]
  set cx [expr {$uy*$z-$uz*$y}]
  set cy [expr {$uz*$x-$ux*$z}]
  set cz [expr {$ux*$y-$uy*$x}]
  set rx [expr {$x*$cosine+$cx*$sine+$ux*$dot*(1.0-$cosine)}]
  set ry [expr {$y*$cosine+$cy*$sine+$uy*$dot*(1.0-$cosine)}]
  set rz [expr {$z*$cosine+$cz*$sine+$uz*$dot*(1.0-$cosine)}]
  return [list [expr {$rx/$scale}] [expr {$ry/$scale}] [expr {$rz/$scale}]]
}

proc mn_m32850_cylinder_residual_max {curve cylinder scale angle dx dy dz samples label} {
  uplevel #0 [list bounds $curve mn_curve_u1 mn_curve_u2]
  set u1 [uplevel #0 {dval mn_curve_u1}]
  set u2 [uplevel #0 {dval mn_curve_u2}]
  if {![string is double -strict $u1] || ![string is double -strict $u2] || $u2 <= $u1} {
    bench_assert {0} "$label curve bounds are measurable"
    return -1.0
  }
  set max_residual 0.0
  set max_parameter $u1
  for {set i 0} {$i < $samples} {incr i} {
    set parameter [expr {$u1+($u2-$u1)*$i/double($samples-1)}]
    set world_point [mn_curve_point $curve $parameter]
    set local_point [mn_inverse_transform_point $world_point $scale $angle $dx $dy $dz]
    lassign $local_point x y z
    if {$cylinder eq "first"} {
      set radial [expr {sqrt(($x-25.8071575178163)**2+($z+373.974517822281)**2)}]
    } else {
      set radial [expr {sqrt(($y-1974.19284248218)**2+($z+373.974517822281)**2)}]
    }
    set residual [expr {abs($radial-408.974517822893)*$scale}]
    if {$residual > $max_residual} { set max_residual $residual; set max_parameter $parameter }
  }
  puts "MN_ANALYTIC_CYLINDER_MAX label=[list $label] samples=$samples cylinder=$cylinder max_distance=$max_residual max_param=$max_parameter"
  return $max_residual
}
