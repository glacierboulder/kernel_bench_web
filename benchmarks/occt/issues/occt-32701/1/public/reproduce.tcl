pload MODELING
set assets [file dirname [info script]]
restore [file join $assets bug32701s.brep] f1
restore [file join $assets bug32701t.brep] t
explode t f
copy t_3 f2
bsection section f1 f2
puts [checkshape section]
puts [nbshapes section]
puts [lprops section]
puts [tolerance section]
foreach edge [explode section e] {puts [lprops $edge]}
exit
