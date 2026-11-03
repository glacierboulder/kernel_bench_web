set ::single20_case {1 0 0}
source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
lassign $::single20_case scale translated healthy
set ox [expr {$translated ? 17.0 : 0.0}]
set oy [expr {$translated ? -29.0 : 0.0}]
set oz [expr {$translated ? 43.0 : 0.0}]
restore [file join [file dirname [info script]] bug25111_s1.draw] first_support
mkface first first_support
if {$healthy} {
    plane second_support 0 0 2 0 0 1
    mkface second second_support -20 20 -20 20
    set expected_length [expr {28*acos(-1)*$scale}]
    set length_limit [expr {1e-5*$scale}]
} else {
    restore [file join [file dirname [info script]] bug25111_s2.draw] second_support
    mkface second second_support
    set expected_length [expr {53.1714*$scale}]
    set length_limit [expr {1e-4*$expected_length}]
}
if {$scale != 1} {tscale first second 0 0 0 $scale}
if {$translated} {ttranslate first second $ox $oy $oz}
set validity [checkshape first]
::single20::assert valid_first [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
set validity [checkshape second]
::single20::assert valid_second [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
::single20::finish
