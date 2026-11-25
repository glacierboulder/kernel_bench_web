pload MODELING
restore [file join [file dirname [info script]] bug28690_m8_faces.brep] a
ttranslate a -20000 -584.41225425562368 0
plane f 0 0 0 1 0 0
mkface f f
bsection r a f
puts [nbshapes r]
puts [lprops r]
foreach e [explode r e] {puts [validrange $e]}
exit
