pload MODELING
restore bug25237_b26.brep a
restore bug25237_b5.brep b
puts "INPUT A [lprops a]"
puts "INPUT B [lprops b]"
foreach scenario {original shifted rotated swapped swapped_shifted swapped_rotated disjoint} {
  restore bug25237_b26.brep a
  restore bug25237_b5.brep b
  switch $scenario {
    shifted - swapped_shifted {ttranslate a 17 -13 9; ttranslate b 17 -13 9}
    rotated - swapped_rotated {trotate a 0 0 0 0 0 1 37; trotate b 0 0 0 0 0 1 37}
  }
  if {$scenario eq "disjoint"} {ttranslate b 0 10 0}
  if {[string match swapped* $scenario]} {bop b a} else {bop a b}
  bopcommon result
  puts "CASE $scenario"
  puts [nbshapes result]
  puts [lprops result]
  explode result e
  set c ""
  if {$scenario ne "disjoint"} {mkcurve c result_1; puts "CURVE [whatis c]"}
}
exit
