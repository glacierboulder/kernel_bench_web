puts "========"
puts "OCC29972: Intersection curve has a weird gap in the middle of it"
puts "========"
puts ""

set GoodNbCurves 6

foreach a [directory res*] {unset $a}

torus s1 -127 84 100 0 0 -1 1 0 0 23 10
cylinder s2 -132 61.5500556793564 131 0 0 -1 1 0 0 10

svalue s1 0 0 v4_t_x0 v4_t_y0 v4_t_z0
svalue s2 0 0 v4_c_x0 v4_c_y0 v4_c_z0
set v4_t_x0 [dval v4_t_x0]; set v4_t_y0 [dval v4_t_y0]; set v4_t_z0 [dval v4_t_z0]
set v4_c_x0 [dval v4_c_x0]; set v4_c_y0 [dval v4_c_y0]; set v4_c_z0 [dval v4_c_z0]
set v4_translate_rc [translate s1 s2 13 -7 5]
svalue s1 0 0 v4_t_x1 v4_t_y1 v4_t_z1
svalue s2 0 0 v4_c_x1 v4_c_y1 v4_c_z1
set v4_t_x1 [dval v4_t_x1]; set v4_t_y1 [dval v4_t_y1]; set v4_t_z1 [dval v4_t_z1]
set v4_c_x1 [dval v4_c_x1]; set v4_c_y1 [dval v4_c_y1]; set v4_c_z1 [dval v4_c_z1]
set v4_te [expr {max(abs(($v4_t_x1-$v4_t_x0)-13),abs(($v4_t_y1-$v4_t_y0)+7),abs(($v4_t_z1-$v4_t_z0)-5))}]
set v4_ce [expr {max(abs(($v4_c_x1-$v4_c_x0)-13),abs(($v4_c_y1-$v4_c_y0)+7),abs(($v4_c_z1-$v4_c_z0)-5))}]
puts "M29972_TRANSLATE rc={$v4_translate_rc} torus_before=($v4_t_x0,$v4_t_y0,$v4_t_z0) torus_after=($v4_t_x1,$v4_t_y1,$v4_t_z1) cylinder_before=($v4_c_x0,$v4_c_y0,$v4_c_z0) cylinder_after=($v4_c_x1,$v4_c_y1,$v4_c_z1) witness_error=($v4_te,$v4_ce)"
if {$v4_te > 1.0e-8 || $v4_ce > 1.0e-8} { error "common translation witness failed" }
puts "__BENCH_ASSERT_PASS__ transform_witness"

intersect res s1 s2 1.0e-4

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