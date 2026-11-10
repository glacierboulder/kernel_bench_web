set here [file dirname [info script]]
source [file join $here .. .. .. single20 assertions.tcl]
source [file join $here .. .. oracle_helpers.tcl]
set inputs [file normalize [file join $here .. .. .. .. .. issues occt-25337 1 public inputs]]
pload MODELING
circle c1 -50 0 0 10
circle c2 -35 0 0 10
mkedge e1 c1
mkedge e2 c2
wire w1 e1
wire w2 e2
mkplane f1 w1
mkplane f2 w2
bop f1 f2
bopfuse fused
bopcommon common
compound common
puts "=== FUSED ==="
set valid_log [checkshape fused]
puts $valid_log
set fused_log [sprops fused]
puts $fused_log
puts [nbshapes fused]
puts "=== COMMON ==="
puts [checkshape common]
set common_log [sprops common]
puts $common_log
puts [nbshapes common]

set r 10.0
set distance 15.0
set overlap 0.0
if {$distance<2*$r} {set overlap [expr {2*$r*$r*acos($distance/(2*$r))-0.5*$distance*sqrt(4*$r*$r-$distance*$distance)}]}
set disk_area [expr {acos(-1.0)*$r*$r}]
set union [expr {2*$disk_area-$overlap}]
set fm [::author20261110::mass $fused_log]
set cm [::author20261110::mass $common_log]
set tolerance [expr {0.003*($r/10.0)*($r/10.0)}]
::single20::assert fuse_area [::author20261110::close $fm $union $tolerance] "observed=$fm expected=$union" numeric
::single20::assert common_area [::author20261110::close $cm $overlap $tolerance] "observed=$cm expected=$overlap" numeric
::single20::assert area_conservation [expr {[::single20::finite $fm] && [::single20::finite $cm] && abs($fm+$cm-2*$disk_area)<=2*$tolerance}] area_sum numeric
::single20::assert fuse_valid [expr {[string first "This shape seems to be valid" $valid_log]>=0}] topology_check

::single20::finish
