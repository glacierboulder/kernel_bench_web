pload MODELING
set assets [file dirname [info script]]
restore [file join $assets OCC13116_sh1.brep] b1
restore [file join $assets OCC13116_sh2.brep] b2
explode b1 f
explode b2 f
mksurface s1 b1_3
mksurface s2 b2_1
mkface f1 s1 0 6.283185307179586 -10 10
mkface f2 s2
ttranslate f2 0 0 0.02
bsection section f1 f2
puts [checkshape section]
puts [nbshapes section]
puts [lprops section]
puts [tolerance section]
foreach edge [explode section e] {puts [lprops $edge]}
exit
