set here [file dirname [info script]]
source [file join $here .. .. .. single20 assertions.tcl]
source [file join $here .. .. oracle_helpers.tcl]
set inputs [file normalize [file join $here .. .. .. .. .. issues occt-30198 1 public inputs]]
pload MODELING
box a 0 0 0 10 10 10
box b 5 0 0 10 10 10
puts OPERATION_STARTED
bfuse result a b
puts ===RESULT===
set valid_log [checkshape result]
puts $valid_log
set shape_log [nbshapes result]
puts $shape_log
set mass_log [vprops result 1e-7]
puts $mass_log


set mass [::author20261110::mass $mass_log]
::single20::assert shape_valid [expr {[string first "This shape seems to be valid" $valid_log]>=0}] topology_check
::single20::assert nonempty [expr {[::author20261110::count $shape_log EDGE]>0 && [::single20::finite $mass] && abs($mass)>1e-7}] "signed_volume=$mass" numeric
::single20::assert analytic_volume [::author20261110::close $mass 1500 0.02] "volume=$mass expected=1500" numeric

::single20::finish
