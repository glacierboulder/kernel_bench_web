source [file join [file dirname [info script]] bootstrap.tcl]
psphere sph 4
box clip 0 -4 -4 4 8 8
bcommon result sph clip
checkshape result
set bc [bopcheck result]
stage3_assert [regexp {This shape seems to be OK} $bc] bop_valid "bopcheck=$bc"
checkprops result -v 134.04128655316
stage3_assert 1 analytic_volume "checkprops enforces analytically derived volume=134.04128655316"

v4_finish
