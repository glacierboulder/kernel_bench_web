set ::single20_case {1.8e-7 10 0}
source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
lassign $::single20_case gap degrees rigid
set lower_second [expr {10.0+$gap}]
box first 10 10 10
box second $lower_second 0 0 10 10 10
explode second f
copy second_1 splitter
trotate splitter 0 5 5 0 1 0 $degrees
mksurface plane_support splitter
mkface splitter plane_support -100 100 -100 100
if {$rigid} {ttranslate first second splitter 17 -29 43}
set validity [checkshape first]
::single20::assert valid_first [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
set validity [checkshape second]
::single20::assert valid_second [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
set validity [checkshape splitter]
::single20::assert valid_splitter [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
::single20::finish
