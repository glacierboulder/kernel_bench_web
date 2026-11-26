pload MODELING
set dir [file dirname [info script]]
restore [file join $dir buc60532a.brep] p
restore [file join $dir buc60532b.brep] t1
restore [file join $dir buc60532c.brep] t2
halfspace h1 t1 20 20 0
halfspace h2 t2 20 20 0
bcut first p h1
bcut result first h2
puts [nbshapes result]
puts [sprops result]
puts [checkshape result]
exit
