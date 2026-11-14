pload MODELING
restore [file join [file dirname [info script]] .. public inputs bug24161_MirrorSolids.brep] m
ttranslate m 20 30 40
explode m
bop m_1 m_2
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
if {[expr {abs($volume - 2339180)}] > 20} {error "Unexpected volume $volume"}
puts CASE_PASS
