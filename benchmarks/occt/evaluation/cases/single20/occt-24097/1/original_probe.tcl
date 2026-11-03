source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
restore [file join [file dirname [info script]] bug24097_face1.brep] first
restore [file join [file dirname [info script]] bug24097_face2.brep] second
bsection result first second
set edges [explode result e]
set vertices [explode result v]
set length [::single20::mass lprops result]
puts "MEASURE length=$length vertices=[llength $vertices] edges=[llength $edges]"
::single20::assert edge_count [expr {[llength $edges]==1}] "edges=[llength $edges] expected=1 screening_only=1" numeric
::single20::assert vertex_count [expr {[llength $vertices]==2}] "vertices=[llength $vertices]" numeric
::single20::assert length [expr {abs($length-0.125) <= 1e-4*0.125}] "length=$length expected=0.125 upstream_relative_epsilon=1e-4" numeric
set validity [checkshape result]
::single20::assert validity [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
::single20::finish
