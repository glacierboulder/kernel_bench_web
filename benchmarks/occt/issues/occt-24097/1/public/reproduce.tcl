pload TOPTEST
set here [file dirname [info script]]
restore [file join $here bug24097_face1.brep] first
restore [file join $here bug24097_face2.brep] second
bsection result first second
checkshape result
checksection result
lprops result
