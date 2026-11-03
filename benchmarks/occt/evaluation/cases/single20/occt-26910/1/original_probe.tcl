source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
restore [file join [file dirname [info script]] bug26910.brep] input
explode input
bclearobjects
bcleartools
baddobjects input_1
baddtools input_2
bfillds
bbuild result
set vertices [explode result v]
::single20::assert intersection_vertices [expr {[llength $vertices]==5}] "vertices=[llength $vertices] expected=5 screen_only=1" numeric
::single20::finish
