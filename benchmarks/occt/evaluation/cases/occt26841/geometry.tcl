proc section_trial {mode} {
  global assetdir
  pload MODELING
  if {$mode eq "control"} {
    plane pa 0 0 0 0 0 1
    plane pb 0 0 0 1 0 0
    mkface left pa -4 4 -4 4
    mkface right pb -3 3 -3 3
  } else {
    restore [file join $assetdir GEN758_nofog.rle] a
    explode a f
    copy a_1 left
    copy a_2 right
    if {$mode eq "translated"} {ttranslate left right 2 -3 1}
    if {$mode eq "swapped"} {copy a_2 left; copy a_1 right}
  }
  bsection result left right
  set counts [nbshapes result]
  set valid [checkshape result]
  if {![regexp {VERTEX\s*:\s*([0-9]+)} $counts -> v] ||
      ![regexp {EDGE\s*:\s*([0-9]+)} $counts -> e] ||
      ![regexp {Mass\s*:\s*([-+.0-9eE]+)} [lprops result] -> length]} {error "unreadable geometry"}
  puts "MEASURE $mode vertices=$v edges=$e length=$length validity=$valid"
  if {![string match "*seems to be valid*" $valid]} {return 0}
  if {$mode eq "control"} {return [expr {$e==1 && $v==2 && abs($length-6)<0.00001}]}
  return [expr {$e==2 && $v==3 && abs($length-22.2575)<=0.001}]
}
