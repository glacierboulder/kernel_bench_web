pload MODELING
restore [file join [file dirname [info script]] bug29843_loc.brep] s
explode s
bclearobjects
bcleartools
baddobjects s_1
baddtools s_2
bfillds
bbop section 4
puts [nbshapes section -t]
puts [lprops section]
puts [bbop result 0]
puts [checkshape result]
puts [bopcheck result]
puts [nbshapes result -t]
puts [vprops result]
exit
