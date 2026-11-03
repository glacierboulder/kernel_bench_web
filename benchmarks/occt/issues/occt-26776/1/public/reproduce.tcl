pload TOPTEST
set here [file dirname [info script]]
restore [file join $here bug26580-plate-2.brep] first
restore [file join $here bug26776_b2.brep] second
bsection result first second
checkshape result
checksection result
lprops result
nbshapes result
