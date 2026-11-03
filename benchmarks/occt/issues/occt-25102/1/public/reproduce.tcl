pload TOPTEST
set here [file dirname [info script]]
restore [file join $here bug25102.brep] input
explode input
copy input_1 first
copy input_2 second
bsection result first second
checkshape result
checksection result
lprops result
nbshapes result
