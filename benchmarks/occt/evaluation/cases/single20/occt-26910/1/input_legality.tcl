set ::single20_case {1 0 0}
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
set validity [checkshape first]
::single20::assert valid_first [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
set validity [checkshape second]
::single20::assert valid_second [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
::single20::finish
