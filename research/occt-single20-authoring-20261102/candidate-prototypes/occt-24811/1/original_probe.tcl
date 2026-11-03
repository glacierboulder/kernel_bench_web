source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
restore [file join [file dirname [info script]] bug24811_e1.brep] first
restore [file join [file dirname [info script]] bug24811_e2.brep] second
bop first second
bopcut result
set edges [explode result e]
set vertices [explode result v]
set length [::single20::mass lprops result]
puts "MEASURE length=$length vertices=[llength $vertices] edges=[llength $edges]"
::single20::assert edge_count [expr {[llength $edges]==4}] "edges=[llength $edges] expected=4 screening_only=1" numeric
set validity [checkshape result]
::single20::assert validity [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
::single20::finish
