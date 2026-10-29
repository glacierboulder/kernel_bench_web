# Score the defect documented by the exact upstream test: section continuity
# between the generated intersection curves. The byte-exact full upstream test
# is retained separately as official_upstream.tcl; xdistcs face residuals are
# measured only by the separate diagnostic, not claimed as passing here.
set v4_dir [file dirname [info script]]
source [file join $v4_dir bootstrap.tcl]
puts "OCC29972 section-continuity oracle; upstream source: official_upstream.tcl"
set GoodNbCurves 6
foreach a [directory res*] {unset $a}
torus s1 -127 84 100 0 0 -1 1 0 0 23 10
cylinder s2 -132 61.5500556793564 131 0 0 -1 1 0 0 10
intersect res s1 s2 1.0e-4
if {[info exists res]} {renamevar res res_1}
bclearobjects
bcleartools
set ic 1
while {1} {
  if {![info exists res_$ic]} {break}
  bounds res_$ic U1 U2
  if {[dval U2-U1] < 1.0e-9} {puts "Error: Wrong curve's range!"}
  mkedge ee res_$ic
  baddobjects ee
  incr ic
}
set v4_curve_count [expr {$ic - 1}]
puts "M29972_SECTION_CURVE_COUNT observed=$v4_curve_count expected=$GoodNbCurves"
stage3_assert [expr {$v4_curve_count == $GoodNbCurves}] curve_count "observed=$v4_curve_count expected=$GoodNbCurves"
bfillds
bbuild rs
v4_section_oracle rs $GoodNbCurves
v4_finish
