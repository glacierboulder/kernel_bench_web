source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
pcylinder c 3 3
explode c e
tcopy c_3 second
ttranslate second 0 6 0
bop c_3 second
bopfuse result
set vertices [explode result v]
set edges [explode result e]
set length [::single20::mass lprops result]
::single20::assert tangent_vertex [expr {[llength $vertices]==3 && [llength $edges]==4}] "vertices=[llength $vertices] edges=[llength $edges]" numeric
::single20::assert circle_lengths [expr {abs($length-12*acos(-1))<1e-6}] "length=$length" numeric
::single20::finish
