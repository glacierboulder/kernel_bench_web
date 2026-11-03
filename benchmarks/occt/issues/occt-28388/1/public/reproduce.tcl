pload TOPTEST
set here [file dirname [info script]]
restore [file join $here bug28388_extKO.brep] input
explode input
bop input_1 input_2
bopcommon result
checkshape result
sprops result
