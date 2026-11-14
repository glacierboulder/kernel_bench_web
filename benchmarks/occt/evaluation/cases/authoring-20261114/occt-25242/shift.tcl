pload MODELING
box a 100 0 0 10 10 10
box b 120 0 0 10 10 10
bfuse r0 a b
bcut result r0 a
set topology [nbshapes result]
set properties [vprops result]
set validity [checkshape result]
puts $topology
puts $properties
puts $validity
if {![regexp -line {^\s*SOLID\s*:\s*1\s*$} $topology]} {error "Expected one solid"}
if {![string match "*This shape seems to be valid*" $validity]} {error "Invalid solid"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} $properties match volume]} {error "Missing volume"}
if {![regexp -line {^\s*X\s*=\s*([-+0-9.eE]+)} $properties match cx]} {error "Missing center of mass"}
if {abs($volume - 1000) > 0.001 || abs($cx - 125) > 0.001} {error "Unexpected volume or position"}
puts TEST_DONE
