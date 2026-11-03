source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
restore [file join [file dirname [info script]] bug28216_initSurf.brep] face
restore [file join [file dirname [info script]] bug28216_solid.brep] solid
bop face solid
bopcommon result
set faces [explode result f]
set edges [explode result e]
set vertices [explode result v]
set area [::single20::mass sprops result]
set validity [checkshape result]
::single20::assert topology [expr {[llength $faces]==1 && [llength $edges]==4 && [llength $vertices]==4}] "faces=[llength $faces] edges=[llength $edges] vertices=[llength $vertices] screen_only=1" numeric
::single20::assert nonzero_area [expr {$area>1e-7}] "area=$area screen_only=1" numeric
::single20::assert validity [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
::single20::finish
