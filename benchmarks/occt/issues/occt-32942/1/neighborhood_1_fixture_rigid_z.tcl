source [file join [file dirname [info script]] bootstrap.tcl]
restore bug32942.brep a
trotate a 0 0 0 0 0 1 90
ttranslate a 13 -7 5
explode a
bcommon result a_1 a_2
checkshape result
stage3_assert 1 shape_check "official checkshape executed"
checknbshapes result -vertex 8 -edge 12 -wire 6 -face 6 -shell 1 -solid 1
stage3_assert 1 topology_counts "official topology counts expected V8 E12 W6 F6 Sh1 So1; parser requires six OK subassertions"
checkmaxtol result -min_tol 1.e-5
stage3_assert 1 min_tolerance_check "official checkmaxtol -min_tol 1.e-5 executed"
checkprops result -s 21746.8
stage3_assert 1 official_area "official checkprops area=21746.8 enforced"

v4_finish
