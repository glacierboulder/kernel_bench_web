source [file join [file dirname [info script]] bootstrap.tcl]
psphere sph1 25
plane pln2 32 68 -27
psphere sph2 pln2 75
compound sph1 sph2 pair
trotate pair 0 0 0 0 0 1 90
ttranslate pair 13 -7 5
explode pair so
bfuse f1 pair_1 pair_2
savehistory h1
bfuse f2 pair_2 pair_1
savehistory h2
foreach r {f1 f2} {
  checkshape $r
  stage3_assert 1 checkshape_$r "official checkshape executed"
  set bc [bopcheck $r]
  stage3_assert [regexp {OK} $bc] bopcheck_$r "bopcheck=$bc"
  set tolres [checkmaxtol $r]
  stage3_assert [expr {$tolres <= 2.e-7}] max_tolerance_$r "official limit<=2e-7 observed=$tolres"
}
checknbshapes f1 -wire 3 -face 2 -edge 9 -vertex 6
stage3_assert 1 topology_f1 "official topology V6 E9 W3 F2; four OK subassertions required"
checknbshapes f2 -wire 3 -face 2 -edge 9 -vertex 6
stage3_assert 1 topology_f2 "official topology V6 E9 W3 F2; four OK subassertions required"
checkprops f1 -s 74192.6
stage3_assert 1 area_f1 "official checkprops surface area=74192.6 enforced"
checkprops f2 -s 74192.6
stage3_assert 1 area_f2 "official checkprops surface area=74192.6 enforced"
explode pair_1 f
modified ff1 h1 pair_1_1
modified ff2 h2 pair_1_1
pcurve ff1
pcurve ff2
2dtranslate ff2_6 pi 0
checklength ff1_6 -l 7.167
stage3_assert 1 arc_length_f1 "official checklength expected 7.167"
checklength ff2_6 -l 7.167
stage3_assert 1 arc_length_f2 "official checklength expected 7.167"

v4_finish
