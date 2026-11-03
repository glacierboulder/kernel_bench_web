source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
proc vertex_coordinates {name} {
    uplevel #0 [list mkpoint measured_point $name]
    uplevel #0 {coord measured_point measured_x measured_y measured_z}
    lassign [uplevel #0 {list [dval measured_x] [dval measured_y] [dval measured_z]}] x y z
    foreach coordinate [list $x $y $z] {
        if {![::single20::finite $coordinate]} {error "non-finite vertex coordinates"}
    }
    return [list $x $y $z]
}
lassign $::single20_case scale translated separated
set ox [expr {$translated ? 17.0 : 0.0}]
set oy [expr {$translated ? -29.0 : 0.0}]
set oz [expr {$translated ? 43.0 : 0.0}]
restore [file join [file dirname [info script]] bug26910.brep] input
explode input
copy input_1 first
copy input_2 second
if {$scale != 1} {tscale first second 0 0 0 $scale}
if {$translated} {ttranslate first second $ox $oy $oz}
if {$separated} {ttranslate second 0 0 [expr {1000*$scale}]}
set expected_points {}
foreach shape {first second} {
    foreach vertex [explode $shape v] {lappend expected_points [vertex_coordinates $vertex]}
}
set expected_length [expr {[::single20::mass lprops first]+[::single20::mass lprops second]}]
compound first second original_edges
set expected_vertices 4
set expected_edges 2
set junction {}
if {!$separated} {
    mkcurve line_curve second
    bounds line_curve low high
    cvalue line_curve low x0 y0 z0
    cvalue line_curve high x1 y1 z1
    set p0 [list [dval x0] [dval y0] [dval z0]]
    set p1 [list [dval x1] [dval y1] [dval z1]]
    lassign $p0 x0 y0 z0
    lassign $p1 x1 y1 z1
    set ratio [expr {($oy-$y0)/($y1-$y0)}]
    set qx [expr {$x0+$ratio*($x1-$x0)}]
    set qy $oy
    set qz [expr {$z0+$ratio*($z1-$z0)}]
    set radius_error [expr {abs(sqrt(pow($qx-$ox,2)+pow($qz-$oz,2))-150*$scale)}]
    if {$ratio <= 0 || $ratio >= 1 || $radius_error > 1e-6*$scale} {
        error "input is outside the independently verified line-circle crossing regime"
    }
    set junction [list $qx $qy $qz]
    lappend expected_points $junction
    set expected_vertices 5
    set expected_edges 4
    puts "ANALYTIC_JUNCTION point=$junction radius_error=$radius_error line_fraction=$ratio"
}
bclearobjects
bcleartools
baddobjects first
baddtools second
set operation_error [catch {bfillds; bbuild result} operation_log]
if {[info exists ::single20_negative]} {
    switch $::single20_negative {
        unchanged {compound first second result}
        empty {compound result}
        shifted {ttranslate result 1000 1000 1000}
    }
}
::single20::assert operation_completed [expr {$operation_error == 0}] "error=$operation_error report=$operation_log"
set vertices {}
set edges {}
catch {
    copy result vertex_source
    copy result edge_source
    set vertices [explode vertex_source v]
    set edges [explode edge_source e]
}
::single20::assert split_topology [expr {[llength $vertices] == $expected_vertices && [llength $edges] == $expected_edges}] "vertices=[llength $vertices] edges=[llength $edges] expected_vertices=$expected_vertices expected_edges=$expected_edges" numeric
set measured_points {}
foreach vertex $vertices {lappend measured_points [vertex_coordinates $vertex]}
set positions_ok [expr {[llength $measured_points] == $expected_vertices}]
set worst_point 0.0
foreach expected $expected_points {
    lassign $expected x y z
    set minimum 1e100
    foreach measured $measured_points {
        lassign $measured mx my mz
        set distance [expr {sqrt(pow($x-$mx,2)+pow($y-$my,2)+pow($z-$mz,2))}]
        set minimum [expr {min($minimum,$distance)}]
    }
    set worst_point [expr {max($worst_point,$minimum)}]
    if {$minimum > 1e-6*$scale} {set positions_ok 0}
}
::single20::assert analytic_vertex_set $positions_ok "max_distance=$worst_point limit=[expr {1e-6*$scale}]" numeric
set degree 0
if {!$separated} {
    lassign $junction qx qy qz
    foreach edge $edges {
        foreach vertex [explode $edge v] {
            lassign [vertex_coordinates $vertex] x y z
            if {sqrt(pow($x-$qx,2)+pow($y-$qy,2)+pow($z-$qz,2)) <= 1e-6*$scale} {incr degree}
        }
    }
}
::single20::assert junction_incidence [expr {$degree == ($separated ? 0 : 4)}] "degree=$degree expected=[expr {$separated ? 0 : 4}]" numeric
set length unknown
set length_ok 0
if {![catch {set length [::single20::mass lprops result]}]} {
    set length_ok [expr {abs($length-$expected_length) <= 1e-5*$scale}]
}
::single20::assert preserved_length $length_ok "observed=$length expected=$expected_length limit=[expr {1e-5*$scale}]" numeric
set valid 0
set validity unavailable
if {![catch {checkshape result} validity]} {
    set valid [expr {[string first "This shape seems to be valid" $validity] >= 0}]
}
::single20::assert shape_valid $valid "checkshape=$validity"
::single20::finish
