source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
restore [file join [file dirname [info script]] bug25542_cylinder.brep] first
restore [file join [file dirname [info script]] bug25542_cone.brep] second
bop first second
bopcommon result
set solids [explode result so]
set faces [explode result f]
set area [::single20::mass sprops result]
set validity [checkshape result]
::single20::assert topology [expr {[llength $solids]==1 && [llength $faces]==3}] "solids=[llength $solids] faces=[llength $faces] screen_only=1" numeric
::single20::assert area [expr {abs($area-6951.3)<=1e-4*6951.3}] "area=$area expected=6951.3 upstream_relative_epsilon=1e-4 screen_only=1" numeric
::single20::assert validity [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
::single20::finish
