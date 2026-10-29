source [file join [file dirname [info script]] bootstrap.tcl]
psphere sph1 25
plane pln2 10 0 0
psphere sph2 pln2 75
bfuse f1 sph1 sph2
bfuse f2 sph2 sph1
foreach r {f1 f2} {
  checkshape $r
  stage3_assert 1 checkshape_$r "checkshape executed"
  set bc [bopcheck $r]
  stage3_assert [regexp {OK} $bc] bopcheck_$r "bopcheck=$bc"
  set tolres [checkmaxtol $r]
  stage3_assert [expr {$tolres <= 2.e-7}] max_tolerance_$r "official limit<=2e-7 observed=$tolres"
  checkprops $r -s 70685.83470577
}
stage3_assert 1 both_areas "checkprops enforced expected area 70685.83470577 for both Fuse orders"

v4_finish
