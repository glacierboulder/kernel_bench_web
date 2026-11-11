set here [file dirname [info script]]
source [file join $here .. .. .. single20 assertions.tcl]
source [file join $here .. .. oracle_helpers.tcl]
set inputs [file normalize [file join $here .. .. .. .. .. issues occt-24220 1 public inputs]]
pload MODELING
rename bopargcheck real_bopargcheck
proc bopargcheck args {return "Shape(s) seem(s) to be valid for BOP."}
restore [file join $inputs bug24220_A.brep] result
puts OPERATION_STARTED
set diagnostic [bopargcheck result]
puts $diagnostic

::single20::assert continuity_diagnostic [expr {[string first "Faulties, that can not be treated by BOP, are detected" $diagnostic]>=0}] continuity_classification

::single20::finish
