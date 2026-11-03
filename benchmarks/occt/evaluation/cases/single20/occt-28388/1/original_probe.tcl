source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
restore [file join [file dirname [info script]] bug28388_extKO.brep] input
explode input
bop input_1 input_2
bopcommon result
set faces [explode result f]
set area [::single20::mass sprops result]
set validity [checkshape result]
::single20::assert nonempty_face [expr {[llength $faces]>0 && $area>1e-7}] "faces=[llength $faces] area=$area screen_only=1" numeric
::single20::assert validity [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
::single20::finish
