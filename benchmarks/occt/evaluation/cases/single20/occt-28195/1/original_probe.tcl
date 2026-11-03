source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
restore [file join [file dirname [info script]] bug28195_solidsKO.brep] input
explode input
bop input_1 input_2
bopcommon result
set solids [explode result so]
set volume [::single20::mass vprops result]
set validity [checkshape result]
::single20::assert nonempty_solid [expr {[llength $solids]>0 && $volume>1e-7}] "solids=[llength $solids] volume=$volume screen_only=1" numeric
::single20::assert validity [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
::single20::finish
