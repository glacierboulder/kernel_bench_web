pload TOPTEST
set here [file dirname [info script]]
restore [file join $here bug25542_cylinder.brep] first
restore [file join $here bug25542_cone.brep] second
bop first second
bopcommon result
checkshape result
sprops result
vprops result
