pload MODELING
set here [file dirname [info script]]
set input [file join $here inputs bug24161_MirrorSolids.brep]
if {![file exists $input]} {set input [file join $here bug24161_MirrorSolids.brep]}
restore $input m
explode m
bop m_1 m_2
bopfuse result
puts [checkshape result]
puts [nbshapes result]
puts [vprops result]
puts SCREEN_DONE
