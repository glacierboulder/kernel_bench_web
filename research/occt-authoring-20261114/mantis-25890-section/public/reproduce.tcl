pload MODELING
set here [file dirname [info script]]
restore [file join $here bug25890_f1.brep] f1
restore [file join $here bug25890_f2.brep] f2

bsection e f1 f2
puts [nbshapes e]
puts [checkshape e]
puts [lprops e]
puts SCREEN_DONE
