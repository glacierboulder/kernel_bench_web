pload TOPTEST
restore [file join [file dirname [info script]] cylinder.brep] cylinder
restore [file join [file dirname [info script]] tool-original.brep] tool
bcut result cylinder tool
checkshape result
vprops result -full
