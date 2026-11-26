pload MODELING
set dir [file dirname [file normalize [info script]]]
foreach mode {original translated swapped control} {
  if {$mode eq "control"} {
    plane pa 0 0 0 0 0 1
    plane pb 0 0 0 1 0 0
    mkface left pa -4 4 -4 4
    mkface right pb -3 3 -3 3
  } else {
    restore [file join $dir GEN758_nofog.rle] a
    explode a f
    copy a_1 left
    copy a_2 right
    if {$mode eq "translated"} {ttranslate left right 2 -3 1}
    if {$mode eq "swapped"} {copy a_2 left; copy a_1 right}
  }
  bsection result left right
  puts "MEASURE $mode [lprops result] [nbshapes result] [checkshape result]"
}
exit
