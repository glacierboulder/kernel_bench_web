set here [file dirname [info script]]
source [file join $here .. .. .. single20 assertions.tcl]
source [file join $here .. .. oracle_helpers.tcl]
set inputs [file normalize [file join $here .. .. .. .. .. issues occt-29038 1 public inputs]]
pload MODELING
restore [file join $inputs bug29038_bfuse_hang.brep] a
explode a
puts OPERATION_STARTED
bfuse result a_1 a_2
compound result
puts ===RESULT===
set valid_log [checkshape result]
puts $valid_log
set shape_log [nbshapes result]
puts $shape_log
set mass_log [sprops result 1e-5]
puts $mass_log


set mass [::author20261110::mass $mass_log]
::single20::assert shape_valid [expr {[string first "This shape seems to be valid" $valid_log]>=0}] topology_check
::single20::assert nonempty [expr {[::author20261110::count $shape_log EDGE]>0 && [::single20::finite $mass] && abs($mass)>1e-7}] "surface_area=$mass" numeric

::single20::assert reference_topology [expr {[::author20261110::count $shape_log FACE]==3 && [::author20261110::count $shape_log EDGE]==9 && [::author20261110::count $shape_log SOLID]==0}] trusted_reference_faces=3_edges=9_open_shape numeric
::single20::assert reference_area [::author20261110::close $mass 8183.52 0.2] "area=$mass reference=8183.52 adaptive_eps=1e-5" numeric

::single20::finish
