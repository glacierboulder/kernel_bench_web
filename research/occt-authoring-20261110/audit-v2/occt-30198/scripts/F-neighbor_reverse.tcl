set here [file dirname [info script]]
source [file join $here .. .. .. single20 assertions.tcl]
source [file join $here .. .. oracle_helpers.tcl]
set inputs [file normalize [file join $here .. .. .. .. .. issues occt-30198 1 public inputs]]
pload MODELING
restore [file join $inputs bug30198_src.brep] a
restore [file join $inputs bug30198_tool.brep] b
copy a tmp
copy b a
copy tmp b
puts OPERATION_STARTED
bfuse result a b
puts ===RESULT===
set valid_log [checkshape result]
puts $valid_log
set shape_log [nbshapes result]
puts $shape_log
set mass_log [vprops result 1e-5]
puts $mass_log
set audit_area_log [sprops result 1e-5]
puts $audit_area_log


set mass [::author20261110::mass $mass_log]
::single20::assert shape_valid [expr {[string first "This shape seems to be valid" $valid_log]>=0}] topology_check
::single20::assert nonempty [expr {[::author20261110::count $shape_log EDGE]>0 && [::single20::finite $mass] && abs($mass)>1e-7}] "signed_volume=$mass" numeric
::single20::assert topology [expr {[::author20261110::count $shape_log FACE]==151 && [::author20261110::count $shape_log WIRE]==163 && [::author20261110::count $shape_log SOLID]==1}] expected_faces=151_wires=163_solids=1 numeric
::single20::assert volume [::author20261110::close $mass 62.6126 0.003] "volume=$mass expected=62.6126" numeric

set audit_area [::author20261110::mass $audit_area_log]
::single20::assert surface_area [::author20261110::close $audit_area 216.217 0.01] "area=$audit_area expected=216.217" numeric

::single20::finish
