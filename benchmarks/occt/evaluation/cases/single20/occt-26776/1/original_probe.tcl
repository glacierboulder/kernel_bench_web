source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
restore [file join [file dirname [info script]] bug26580-plate-2.brep] first
restore [file join [file dirname [info script]] bug26776_b2.brep] second
bsection result first second
set edges [explode result e]
set vertices [explode result v]
set length [::single20::mass lprops result]
set validity [checkshape result]
::single20::assert branch [expr {[llength $edges]==1 && [llength $vertices]==2}] "edges=[llength $edges] vertices=[llength $vertices] screen_only=1" numeric
::single20::assert length [expr {abs($length-27.3439)<=1e-4*27.3439}] "length=$length expected=27.3439 upstream_relative_epsilon=1e-4 screen_only=1" numeric
::single20::assert validity [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
::single20::finish
