pload TOPTEST
restore [file join [file dirname [info script]] bug26910.brep] input
explode input
bclearobjects
bcleartools
baddobjects input_1
baddtools input_2
bfillds
bbuild result
nbshapes result
checkshape result
lprops result
