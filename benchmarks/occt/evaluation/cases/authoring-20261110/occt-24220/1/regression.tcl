set here [file dirname [info script]]
source [file join $here .. .. .. single20 assertions.tcl]
source [file join $here .. .. oracle_helpers.tcl]
set inputs [file normalize [file join $here .. .. .. .. .. issues occt-24220 1 public inputs]]
pload MODELING
box result 10 10 10
puts OPERATION_STARTED
set diagnostic [bopargcheck result]
puts $diagnostic

::single20::assert continuity_diagnostic [expr {!([string first "Faulties, that can not be treated by BOP, are detected" $diagnostic]>=0)}] continuity_classification

::single20::finish
