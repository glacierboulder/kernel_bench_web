pload MODELING
set here [file dirname [info script]]
restore [file join $here output.brep] s
explode s E
fillet rs s 0.1 s_8 0.1 s_27
puts "TEST_DONE issue=847"
