pload TOPTEST
set here [file dirname [info script]]
restore [file join $here bug24429_s1.draw] first
restore [file join $here bug24429_s2.draw] second
intersect result first second
whatis result
