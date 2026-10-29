source [file join [file dirname [info script]] bootstrap.tcl]
restore bug32721.brep prism
pcone cone 6 0 10
compound cone prism pair
trotate pair 0 0 0 0 0 1 90
ttranslate pair 13 -7 5
explode pair so
if {![isdraw pair_1] || ![isdraw pair_2]} {puts "Error: transformed input compound did not yield two solids"} else {stage3_assert 1 operands_created "explode pair so yielded pair_1 and pair_2"}
bop pair_1 pair_2
bopfuse r1
bopcommon r2
bopcut r3
boptuc r4
checkshape r1
stage3_assert 1 checkshape_r1 "official checkshape command executed"
checknbshapes r1 -t -vertex 8 -edge 17 -wire 8 -face 8 -shell 1 -solid 1
stage3_assert 1 topology_r1 "official r1 topology counts; parser requires six OK subassertions"
checkshape r2
stage3_assert 1 checkshape_r2 "official checkshape command executed"
checknbshapes r2 -t -vertex 3 -edge 7 -wire 4 -face 4 -shell 1 -solid 1
stage3_assert 1 topology_r2 "official r2 topology counts; parser requires six OK subassertions"
checkshape r3
stage3_assert 1 checkshape_r3 "official checkshape command executed"
checknbshapes r3 -t -vertex 4 -edge 10 -wire 4 -face 4 -shell 1 -solid 1
stage3_assert 1 topology_r3 "official r3 topology counts; parser requires six OK subassertions"
checkshape r4
stage3_assert 1 checkshape_r4 "official checkshape command executed"
checknbshapes r4 -t -vertex 7 -edge 14 -wire 8 -face 8 -shell 2 -solid 2
stage3_assert 1 topology_r4 "official r4 topology counts; parser requires six OK subassertions"
set tolres [checkmaxtol r1]
stage3_assert [expr {$tolres <= 0.0002}] max_tolerance_r1 "expected<=0.0002 observed=$tolres"
checkprops r1 -s 388.634 -v 406.357
stage3_assert 1 official_props_r1 "area=388.634 volume=406.357; checkprops enforced"
checkprops r2 -s 57.8605 -v 22.8116
stage3_assert 1 official_props_r2 "area=57.8605 volume=22.8116; checkprops enforced"
checkprops r3 -s 358.735 -v 354.179
stage3_assert 1 official_props_r3 "area=358.735 volume=354.179; checkprops enforced"
checkprops r4 -s 87.7592 -v 29.3659
stage3_assert 1 official_props_r4 "area=87.7592 volume=29.3659; checkprops enforced"

v4_finish
