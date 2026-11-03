pload TOPTEST
set here [file dirname [info script]]
restore [file join $here bug28216_initSurf.brep] first
restore [file join $here bug28216_solid.brep] second
bop first second
bopcommon result
checkshape result
sprops result
