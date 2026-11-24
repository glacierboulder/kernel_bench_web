pload MODELING
restore [file join [file dirname [info script]] bug30760_shapes.brep] model
explode model
bclearobjects
bcleartools
baddobjects model_1
baddtools model_2
bfillds
bbop overlap 0
puts [checkshape overlap]
puts [nbshapes overlap]
puts [vprops overlap]
exit
