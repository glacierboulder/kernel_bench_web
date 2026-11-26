pload MODELING
restore [file join [file dirname [info script]] GEN758_nofog.rle] a
explode a f
bsection result a_1 a_2
puts [nbshapes result]
puts [lprops result]
puts [checkshape result]
exit
