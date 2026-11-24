pload MODELING
set dir [file dirname [info script]]
restore [file join $dir bug30354_Face_14.brep] sheet
restore [file join $dir bug30354_vol_neg.brep] solid
bclearobjects
bcleartools
baddobjects sheet
baddtools solid
bfillds
bbop result 4
puts [nbshapes result -t]
puts [lprops result]
puts [checkshape result]
exit
