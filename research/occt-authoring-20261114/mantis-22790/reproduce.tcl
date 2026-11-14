pload MODELING
puts "============"
puts "OCC22790"
puts "============"
puts ""
#######################################################################
# Boolean operation Fuse fails.
#######################################################################

set BugNumber OCC22790

puts "Load shape ..."
restore [file join [file dirname [info script]] OCC22790-cx.brep] b 

explode b
copy b_1 b1
copy b_3 b2

bop b1 b2

bopfuse result


if {![regexp -line {^\s*FACE\s*:\s*2\s*$} [nbshapes result]]} {error "unexpected topology"}
if {![string match "*This shape seems to be valid*" [checkshape result]]} {error "invalid geometry"}
set log [sprops result]
puts $log
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} $log full measured]} {error "missing measure"}
if {abs($measured-1214080000.0)>20000.0} {error "unexpected measure $measured"}

puts CASE_PASS
