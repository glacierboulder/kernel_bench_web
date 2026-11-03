pload TOPTEST
restore [file join [file dirname [info script]] bug26243_anc101.brep] first
tcopy first second
trotate second 155 100.75 0 0 0 1 90
bcommon result first second
checkshape result
sprops result
vprops result
