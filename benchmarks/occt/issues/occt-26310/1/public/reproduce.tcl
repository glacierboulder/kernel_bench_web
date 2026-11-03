pload TOPTEST
set here [file dirname [info script]]
restore [file join $here OCC26310-b1.brep] first
restore [file join $here OCC26310-b2.brep] second
explode first f
explode second f
bopcurves first_1 second_1 -2d
bsection result first second
checkshape result
checksection result
