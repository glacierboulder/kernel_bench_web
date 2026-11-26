pload MODELING
set dir [file dirname [file normalize [info script]]]
foreach mode {original translated rotated control} {
  if {$mode eq "control"} {
    box p 10 10 10
    box h1 4 -1 -1 8 12 12
    box h2 -1 3 -1 6 9 12
  } else {
    restore [file join $dir buc60532a.brep] p
    restore [file join $dir buc60532b.brep] t1
    restore [file join $dir buc60532c.brep] t2
    halfspace h1 t1 20 20 0
    halfspace h2 t2 20 20 0
    if {$mode eq "translated"} {ttranslate p h1 h2 1 -2 3}
    if {$mode eq "rotated"} {trotate p h1 h2 0 0 0 0 0 1 25}
  }
  bcut res1 p h1
  bcut result res1 h2
  puts "MEASURE $mode [sprops result] [nbshapes result] [checkshape result]"
}
exit
