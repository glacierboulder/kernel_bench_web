source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
restore [file join [file dirname [info script]] bug25102.brep] input
explode input
bsection result input_1 input_2
set edges [explode result e]
set vertices [explode result v]
set length [::single20::mass lprops result]
puts "MEASURE length=$length vertices=[llength $vertices] edges=[llength $edges]"
::single20::assert edge_count [expr {[llength $edges]==44}] "edges=[llength $edges] expected=44 screening_only=1" numeric
::single20::assert length [expr {abs($length-49.734) <= 1e-4*49.734}] "length=$length expected=49.734 upstream_relative_epsilon=1e-4" numeric
set validity [checkshape result]
::single20::assert validity [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
::single20::finish
