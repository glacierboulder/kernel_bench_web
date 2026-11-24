pload MODELING
restore [file join [file dirname [info script]] bug26795_c.brep] c
explode c f
line l 20004.7983876926 2164.22470816234 210.858020395251 -0.716336050762455 0.65536108806844 0.239508886314894
mkedge e l -0.2 0.2
settolerance e 0.04
bclearobjects
bcleartools
baddobjects c_2
baddtools e
bfillds
bsplit c_2
bclearobjects
bcleartools
baddobjects e c_1
baddtools c_2
bfillds
bbop result 4
puts [checkshape result]
puts [nbshapes result]
puts [lprops result]
exit
