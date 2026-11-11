set here [file dirname [info script]]
source [file join $here .. .. .. single20 assertions.tcl]
source [file join $here .. .. oracle_helpers.tcl]
set inputs [file normalize [file join $here .. .. .. .. .. issues occt-23933 1 public inputs]]
pload MODELING
box healthy 10 20 30
::single20::assert healthy_valid [string match {*seem(s) to be valid for BOP*} [bopargcheck healthy]] healthy_box
box left 10 10 10
box right 5 5 5 10 10 10
compound left right intersecting
set report [bopargcheck intersecting]
puts "OBSERVED_TRUE_INTERFERENCE=$report"
::single20::assert real_interference_detected [string match {*Faulties*detected*} $report] overlapping_solids

::single20::finish
