source [file join [file dirname [info script]] bootstrap.tcl]
plane pln1 50 50 50
psphere s1 pln1 15
psphere s2 pln1 10
bcut ss s1 s2
box bb 100 100 100
bcommon result bb ss
checkshape result
stage3_assert 1 shape_check "checkshape executed"
set bc [bopcheck result]
stage3_assert [regexp {This shape seems to be OK} $bc] bop_valid "bopcheck=$bc"
set tolres [checkmaxtol result]
stage3_assert [expr {$tolres <= 2.e-7}] max_tolerance "official limit<=2e-7 observed=$tolres"
checkprops result -v 9948.3767363677
stage3_assert 1 shell_volume "contained shell analytic volume 9948.3767363677; checkprops enforced"

v4_finish
