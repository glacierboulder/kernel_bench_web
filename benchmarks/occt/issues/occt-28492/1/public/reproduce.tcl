pload MODELING
set data [file dirname [info script]]
restore [file join $data a350.brep] a
restore [file join $data b350.brep] b
bsection result a b
puts [checkshape result]
puts [nbshapes result]
puts [lprops result]
puts [tolerance result]
foreach edge [explode result e] {puts [lprops $edge]}
exit
