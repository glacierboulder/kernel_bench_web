puts "========"
puts "OCC29972: Intersection curve has a weird gap in the middle of it"
puts "========"
puts ""

set GoodNbCurves 6

foreach a [directory res*] {unset $a}

torus s1 -127 84 100 0 0 -1 1 0 0 23 10
cylinder s2 -132 61.5500556793564 131 0 0 -1 1 0 0 10

intersect res s2 s1 1.0e-4
puts "M29972_OPERAND_ORDER=s2,s1"
puts "__BENCH_ASSERT_PASS__ operand_order"

if { [info exists res] } {
  #Only variable "res" exists
  renamevar res res_1
}

bclearobjects
bcleartools

set ic 1
set AllowRepeat 1
while { $AllowRepeat != 0 } {
  if { ![info exists res_$ic] } {
    set AllowRepeat 0
  } else {
    bounds res_$ic U1 U2
    
    if {[dval U2-U1] < 1.0e-9} {
      puts "Error: Wrong curve's range!"
    }
    
    
    mkedge ee res_$ic
    baddobjects ee
    
    incr ic
  }
}
set v4_curve_total [expr {$ic - 1}]
puts "M29972_CURVE_TOTAL=$v4_curve_total expected=6"
stage3_assert [expr {$v4_curve_total == 6}] curve_count "observed=$v4_curve_total expected=6"

# Check of gaps between intersection curves
bfillds
bbuild rs

v4_section_oracle rs $GoodNbCurves

smallview
don res_*

fit
don s1 s2
disp res_*

checkview -screenshot -2d -path ${imagedir}/${test_image}.png