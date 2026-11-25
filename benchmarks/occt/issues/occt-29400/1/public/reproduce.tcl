pload MODELING
restore [file join [file dirname [info script]] bug29400_edges.brep] input
bclearobjects
bcleartools
baddcompound input
bfillds
bbuild result
puts [nbshapes result]
puts [lprops result]
puts [checkshape result]
puts [bopcheck result]
exit
