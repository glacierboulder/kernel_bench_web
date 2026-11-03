source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
restore [file join [file dirname [info script]] bug28274_tmp.brep] input
bnondestructive 1
set faces [explode input f]
eval mkvolume result $faces
set solids [explode result so]
set volume [::single20::mass vprops result]
set validity [checkshape result]
::single20::assert solid_count [expr {[llength $solids]==3}] "solids=[llength $solids] expected=3 screen_only=1" numeric
::single20::assert volume [expr {abs($volume-741.787)<=1e-4*741.787}] "volume=$volume expected=741.787 upstream_relative_epsilon=1e-4 screen_only=1" numeric
::single20::assert validity [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
::single20::finish
