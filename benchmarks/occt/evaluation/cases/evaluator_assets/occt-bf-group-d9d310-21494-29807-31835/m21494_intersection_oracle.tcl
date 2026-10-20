# Hidden geometric oracle for the two declared cone/sphere calibrations.
# Input parameters and expected roots are frozen in the case wrapper scripts.
source [file join [file dirname [file normalize [info script]]] official_9bc5f585_intss_begin.tcl]

pcone c $bf_cone_radius 0 $bf_cone_height
psphere s $bf_sphere_radius
explode c f
explode s f
mksurface sc c_1
mksurface ss s_1

intersect res sc ss
set res_type [whatis res]
if {[string first "3d curve" $res_type] >= 0} {
  renamevar res res_1
}

set bf_curves {}
set bf_curve_index 1
while {$bf_curve_index <= 32} {
  if {[catch {whatis res_$bf_curve_index} bf_curve_type]} { break }
  if {[string first "3d curve" $bf_curve_type] < 0} {
    break
  }
  lappend bf_curves res_$bf_curve_index
  incr bf_curve_index
}
set bf_curve_count [llength $bf_curves]
set bf_oracle_ok 1
if {$bf_curve_count != $bf_expected_curve_count} {
  puts "Error: BF expected $bf_expected_curve_count cone/sphere curves, found $bf_curve_count"
  set bf_oracle_ok 0
}

set bf_point_count 0
for {set bf_point_index 1} {$bf_point_index <= 32} {incr bf_point_index} {
  if {[info exist res_p_$bf_point_index]} {
    incr bf_point_count
  }
}
if {$bf_point_count != $bf_expected_point_count} {
  puts "Error: BF expected $bf_expected_point_count isolated intersection points, found $bf_point_count"
  set bf_oracle_ok 0
}

# cvalue writes DRAW variables. Read their numeric values with dval, then do
# abs/sqrt comparisons in Tcl expr; DRAW's dval parser does not accept abs/max
# around DRAW variables consistently.
proc bf_read_ring_sample {theCurve theParameter} {
  uplevel #0 [list cvalue $theCurve $theParameter x y z dx dy dz]
  set xv [uplevel #0 {dval x}]
  set yv [uplevel #0 {dval y}]
  set zv [uplevel #0 {dval z}]
  foreach value [list $xv $yv $zv] {
    if {![string is double -strict $value]} {
      return -code error "BF_ORACLE_EVAL_ERROR: DRAW coordinate read failed"
    }
  }
  set rho [expr {sqrt($xv*$xv+$yv*$yv)}]
  return [list $xv $yv $zv $rho]
}

proc bf_check_ring_curve {theCurve theRoot theTolerance} {
  lassign $theRoot expected_z expected_rho
  uplevel #0 [list bounds $theCurve U1 U2]
  set u1 [uplevel #0 {dval U1}]
  set u2 [uplevel #0 {dval U2}]
  if {![string is double -strict $u1] || ![string is double -strict $u2]} {
    return -code error "BF_ORACLE_EVAL_ERROR: DRAW curve bounds could not be read"
  }
  if {$u2 - $u1 <= 1.0e-9} {
    puts "Error: degenerate curve range for $theCurve"
    return 0
  }
  if {[catch {bf_read_ring_sample $theCurve $u1} start_sample] ||
      [catch {bf_read_ring_sample $theCurve $u2} end_sample]} {
    return -code error "BF_ORACLE_EVAL_ERROR: could not sample curve endpoints"
  }
  lassign $start_sample x1 y1 z1 rho1
  lassign $end_sample x2 y2 z2 rho2
  set endpoint_gap [expr {sqrt(($x1-$x2)*($x1-$x2)+($y1-$y2)*($y1-$y2)+($z1-$z2)*($z1-$z2))}]
  puts "BF_ORACLE_ENDPOINT_GAP_$theCurve=$endpoint_gap"
  if {$endpoint_gap > $theTolerance} {
    puts "Error: $theCurve is not closed; endpoint gap=$endpoint_gap"
    return 0
  }
  for {set sample 1} {$sample <= 8} {incr sample} {
    set u [expr {$u1+($u2-$u1)*$sample/9.0}]
    if {[catch {bf_read_ring_sample $theCurve $u} sample_values]} {
      return -code error $sample_values
    }
    lassign $sample_values xv yv zv rho
    set z_error [expr {abs($zv-$expected_z)}]
    set r_error [expr {abs($rho-$expected_rho)}]
    puts "BF_ORACLE_SAMPLE_$theCurve\_$sample=$xv,$yv,$zv,$rho"
    if {$z_error > $theTolerance || $r_error > $theTolerance} {
      puts "Error: $theCurve differs from its assigned analytic root: z_error=$z_error radius_error=$r_error"
      return 0
    }
  }
  return 1
}

if {$bf_curve_count > 0} {
  CheckIntersectionResult sc ss $bf_curves 100 2.0e-7 2.0e-7
}

# Match each measured curve to one distinct analytic root using a midpoint
# sample. Then validate every sample against that fixed root. This prevents
# two duplicate curves near one root from satisfying the two-root oracle.
set bf_assigned_roots {}
set bf_root_checks 0
foreach bf_curve $bf_curves {
  uplevel #0 [list bounds $bf_curve U1 U2]
  set bf_u1 [uplevel #0 {dval U1}]
  set bf_u2 [uplevel #0 {dval U2}]
  set bf_mid [expr {($bf_u1+$bf_u2)/2.0}]
  if {[catch {bf_read_ring_sample $bf_curve $bf_mid} bf_probe]} {
    puts $bf_probe
    set bf_oracle_ok 0
    continue
  }
  lassign $bf_probe px py pz prho
  set best_index -1
  set best_metric 1.0e100
  set root_index 0
  foreach root $bf_expected_roots {
    lassign $root root_z root_rho
    set metric [expr {sqrt(($pz-$root_z)*($pz-$root_z)+($prho-$root_rho)*($prho-$root_rho))}]
    if {$metric < $best_metric} {
      set best_metric $metric
      set best_index $root_index
    }
    incr root_index
  }
  if {$best_index < 0} {
    puts "BF_ORACLE_EVAL_ERROR: no analytic root available for $bf_curve"
    set bf_oracle_ok 0
    continue
  }
  if {[lsearch -exact $bf_assigned_roots $best_index] >= 0} {
    puts "Error: multiple intersection curves map to analytic root index $best_index"
    set bf_oracle_ok 0
    continue
  }
  lappend bf_assigned_roots $best_index
  set assigned_root [lindex $bf_expected_roots $best_index]
  if {[catch {bf_check_ring_curve $bf_curve $assigned_root 2.0e-5} curve_ok]} {
    puts $curve_ok
    set bf_oracle_ok 0
    continue
  }
  if {!$curve_ok} {
    set bf_oracle_ok 0
  } else {
    incr bf_root_checks
  }
}
if {[llength $bf_assigned_roots] != $bf_expected_curve_count ||
    $bf_root_checks != $bf_expected_curve_count} {
  puts "Error: analytic roots were not covered one-to-one by valid curves"
  set bf_oracle_ok 0
}

puts "BF_ORACLE_CURVE_COUNT=$bf_curve_count"
puts "BF_ORACLE_ISOLATED_POINT_COUNT=$bf_point_count"
puts "BF_ORACLE_ROOT_CURVES_CHECKED=$bf_root_checks"
puts "BF_ORACLE_ASSIGNED_ROOTS=$bf_assigned_roots"
if {$bf_oracle_ok} {
  puts "BF_HIDDEN_GEOMETRY_ORACLE=pass"
} else {
  puts "BF_HIDDEN_GEOMETRY_ORACLE=checked"
}
