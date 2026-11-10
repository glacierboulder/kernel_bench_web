set here [file dirname [info script]]
source [file join $here .. .. .. single20 assertions.tcl]
source [file join $here .. .. oracle_helpers.tcl]
set inputs [file normalize [file join $here .. .. .. .. .. issues occt-23933 1 public inputs]]
pload MODELING
restore [file join $inputs bug23933_a.brep] a
restore [file join $inputs bug23933_b.brep] b

set av [checkshape a]; set bv [checkshape b]
::single20::assert inputs_valid [expr {[string match {*seems to be valid*} $av] && [string match {*seems to be valid*} $bv]}] input_topology
bfuse result a b
::single20::assert output_valid [string match {*seems to be valid*} [checkshape result]] output_topology
set report [bopargcheck result]
puts "OBSERVED_BOPARGCHECK=$report"
::single20::assert no_false_self_intersection [string match {*seem(s) to be valid for BOP*} $report] checker_verdict

set audit_shape [nbshapes result]
::single20::assert nonempty_result [expr {[::author20261110::count $audit_shape FACE]>0 && [::author20261110::count $audit_shape EDGE]>0}] fused_shape_not_empty numeric

::single20::finish
