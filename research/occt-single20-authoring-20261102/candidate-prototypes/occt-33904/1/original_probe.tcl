source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
set thickness 3e-5
set radius 200.0
set height 100.0
set angle 5.0
set degrees [expr {$angle*180.0/acos(-1)}]
pcylinder first $radius $height $degrees
pcylinder second [expr {$radius-$thickness}] $height $degrees
bcut result first second
set expected [expr {0.5*$angle*$height*(2*$radius*$thickness-$thickness*$thickness)}]
set volume [::single20::mass vprops result]
set validity [checkshape result]
::single20::assert hollow_volume [expr {abs($volume-$expected)<=1e-6}] "volume=$volume expected=$expected limit=1e-6" numeric
::single20::assert valid_result [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
::single20::finish
