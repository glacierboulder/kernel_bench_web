pload MODELING
restore [file join [file dirname [info script]] bug24811_e1.brep] a
restore [file join [file dirname [info script]] bug24811_e2.brep] b

bop a b
bopcut result
puts "PARTS [llength [explode result]]"
puts [nbshapes result]
puts [checkshape result]
puts [vprops result]
puts [lprops result]


puts PUBLIC_REPRO_COMPLETE
