pload TOPTEST
set here [file dirname [info script]]
restore [file join $here bug25342_pump2.brep] input
explode input
copy input_1 first
copy input_2 second
bop first second
bopsection result
checkshape result
checksection result
lprops result
nbshapes result
