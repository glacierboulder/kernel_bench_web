pload MODELING
box a 10 10 10
box b 5 0 0 10 10 10
bop a b
bopfuse result

set validity [checkshape result]
set topology [nbshapes result]
set properties [vprops result]
puts $validity
puts $topology
puts $properties
if {![string match "*This shape seems to be valid*" $validity]} {error "Invalid result"}
if {![regexp -line {^\s*SOLID\s*:\s*1\s*$} $topology]} {error "Expected one solid"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} $properties match volume]} {error "Missing volume"}
if {[expr {abs($volume - 1500)}] > 0.001} {error "Unexpected volume $volume"}
puts TEST_DONE
