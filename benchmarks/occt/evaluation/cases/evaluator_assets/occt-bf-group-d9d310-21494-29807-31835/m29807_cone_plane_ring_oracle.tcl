# Analytic geometry oracle for the hidden cone/plane control.
source [file join [file dirname [file normalize [info script]]] official_9bc5f585_intss_begin.tcl]

pcone cone $bf_cone_base_radius $bf_cone_top_radius $bf_cone_height
explode cone f
mksurface cone_surface cone_1
plane cut_plane 0 0 $bf_plane_z 0 0 1

puts "BF_INPUT_CONE=[whatis cone]"
puts "BF_INPUT_CONE_SURFACE=[whatis cone_surface]"
puts "BF_INPUT_PLANE=[whatis cut_plane]"

intersect res cone_surface cut_plane
set bf_result_type [whatis res]
if {[string first "3d curve" $bf_result_type] >= 0} {
  renamevar res res_1
}

set bf_curves {}
for {set i 1} {$i <= 16} {incr i} {
  if {[catch {whatis res_$i} bf_type]} { break }
  if {[string first "3d curve" $bf_type] < 0} { break }
  lappend bf_curves res_$i
}
set bf_curve_count [llength $bf_curves]
set bf_point_count 0
for {set i 1} {$i <= 16} {incr i} {
  if {[info exist res_p_$i]} {
    incr bf_point_count
  }
}
puts "BF_ORACLE_CURVE_COUNT=$bf_curve_count"
puts "BF_ORACLE_ISOLATED_POINT_COUNT=$bf_point_count"

set bf_oracle_ok 1
if {$bf_curve_count != $bf_expected_curve_count} {
  puts "Error: expected one cone/plane intersection curve, found $bf_curve_count"
  set bf_oracle_ok 0
}
if {$bf_point_count != $bf_expected_point_count} {
  puts "Error: expected no isolated cone/plane intersection points, found $bf_point_count"
  set bf_oracle_ok 0
}

if {$bf_curve_count == 1} {
  set bf_curve [lindex $bf_curves 0]
  bounds $bf_curve U1 U2
  set bf_u1 [dval U1]
  set bf_u2 [dval U2]
  if {$bf_u2 - $bf_u1 <= 1.0e-9} {
    puts "Error: degenerate parameter range for $bf_curve"
    set bf_oracle_ok 0
  } else {
    cvalue $bf_curve $bf_u1 x1 y1 z1 dx1 dy1 dz1
    cvalue $bf_curve $bf_u2 x2 y2 z2 dx2 dy2 dz2
    set x1v [dval x1]
    set y1v [dval y1]
    set z1v [dval z1]
    set x2v [dval x2]
    set y2v [dval y2]
    set z2v [dval z2]
    set bf_gap [expr {sqrt(($x1v-$x2v)*($x1v-$x2v)+($y1v-$y2v)*($y1v-$y2v)+($z1v-$z2v)*($z1v-$z2v))}]
    puts "BF_ORACLE_ENDPOINT_GAP=$bf_gap"
    if {$bf_gap > 1.0e-6} {
      puts "Error: intersection curve is not closed; endpoint gap=$bf_gap"
      set bf_oracle_ok 0
    }
    for {set sample 1} {$sample <= 16} {incr sample} {
      set u [expr {$bf_u1+($bf_u2-$bf_u1)*$sample/17.0}]
      cvalue $bf_curve $u x y z dx dy dz
      set xv [dval x]
      set yv [dval y]
      set zv [dval z]
      if {![string is double -strict $xv] || ![string is double -strict $yv] || ![string is double -strict $zv]} {
        puts "BF_ORACLE_EVAL_ERROR: DRAW coordinate read failed at sample $sample"
        set bf_oracle_ok 0
        continue
      }
      set rho [expr {sqrt($xv*$xv+$yv*$yv)}]
      set z_error [expr {abs($zv-$bf_expected_z)}]
      set r_error [expr {abs($rho-$bf_expected_radius)}]
      puts "BF_ORACLE_SAMPLE_$sample=$xv,$yv,$zv,$rho"
      if {$z_error > 2.0e-6 || $r_error > 2.0e-6} {
        puts "Error: sample $sample differs from analytic ring: z_error=$z_error radius_error=$r_error"
        set bf_oracle_ok 0
      }
    }
    CheckIntersectionResult cone_surface cut_plane [list $bf_curve] 100 2.0e-7 2.0e-7
  }
}

puts "BF_ORACLE_RADIUS=$bf_expected_radius"
puts "BF_ORACLE_Z=$bf_expected_z"
if {$bf_oracle_ok} {
  puts "BF_HIDDEN_GEOMETRY_ORACLE=pass"
} else {
  puts "BF_HIDDEN_GEOMETRY_ORACLE=checked"
}
