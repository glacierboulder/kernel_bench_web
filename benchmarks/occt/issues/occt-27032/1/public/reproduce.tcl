pload MODELING
restore [file join [file dirname [info script]] OCC27032_sh.brep] shapes
explode shapes
bsection section shapes_1 shapes_2
puts [nbshapes section]
puts [lprops section]
bcut result shapes_1 shapes_2
puts [sprops result]
puts [checkshape result]
exit
