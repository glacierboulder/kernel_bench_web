source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
restore [file join [file dirname [info script]] bug27221.brep] input
explode input
mkplane face input_2
prism tool face -25 0 0
bcut result input_1 tool
set solids [explode result so]
set volume [::single20::mass vprops result]
set validity [checkshape result]
::single20::assert solid_count [expr {[llength $solids]==1}] "solids=[llength $solids] expected=1 screen_only=1" numeric
::single20::assert volume [expr {abs($volume-56860.2)<=1e-4*56860.2}] "volume=$volume expected=56860.2 upstream_relative_epsilon=1e-4 screen_only=1" numeric
::single20::assert validity [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
::single20::finish
