source [file join [file dirname [info script]] bootstrap.tcl]
plane pln1 51.899912462 99.996691888 62.33204004
psphere s1 pln1 15
psphere s2 pln1 10
bcut ss s1 s2
box bb 100 100 100
compound bb ss pair
trotate pair 0 0 0 0 0 1 90
ttranslate pair 13 -7 5
explode pair so
bcommon result pair_1 pair_2
checkshape result
stage3_assert 1 shape_check "official checkshape executed"
checknbshapes result -solid 1 -shell 1 -face 3 -wire 6 -edge 8 -vertex 6
stage3_assert 1 topology_counts "official result topology solid1 shell1 face3 wire6 edge8 vertex6"
set tolres [checkmaxtol result]
stage3_assert [expr {$tolres <= 2.e-7}] max_tolerance "official limit<=2e-7 observed=$tolres"
checkprops result -v 4975.49
stage3_assert 1 official_volume "official checkprops volume=4975.49 enforced"

v4_finish
