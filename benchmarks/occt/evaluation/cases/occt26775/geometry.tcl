proc section_trial {mode} {
  global assetdir
  pload MODELING
  if {$mode eq "control"} {
    box p 10 10 10
    box h1 4 -1 -1 8 12 12
    box h2 -1 3 -1 6 9 12
  } else {
    restore [file join $assetdir buc60532a.brep] p
    restore [file join $assetdir buc60532b.brep] t1
    restore [file join $assetdir buc60532c.brep] t2
    halfspace h1 t1 20 20 0
    halfspace h2 t2 20 20 0
    if {$mode eq "translated"} {ttranslate p h1 h2 1 -2 3}
    if {$mode eq "rotated"} {trotate p h1 h2 0 0 0 0 0 1 25}
  }
  bcut first p h1
  bcut result first h2
  set counts [nbshapes result]
  foreach k {VERTEX EDGE FACE} {
    if {![regexp [format {%s\s*:\s*([0-9]+)} $k] $counts -> n($k)]} {error "missing topology"}
  }
  if {![regexp {Mass\s*:\s*([-+.0-9eE]+)} [sprops result] -> a]} {error "missing area"}
  set valid [checkshape result]
  puts "MEASURE $mode vertices=$n(VERTEX) edges=$n(EDGE) area=$a faces=$n(FACE) validity=$valid"
  if {![string match "*seems to be valid*" $valid]} {return 0}
  if {$mode eq "control"} {return [expr {$n(VERTEX)==8 && $n(EDGE)==12 && $n(FACE)==6 && abs($a-164)<0.00001}]}
  return [expr {$n(VERTEX)==5 && $n(EDGE)==5 && $n(FACE)==1 && abs($a-78.7016)<=0.1}]
}
