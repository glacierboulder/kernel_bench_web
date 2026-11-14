pload MODELING
puts "============"
puts "OCC25385"
puts "============"
puts ""
#######################################################################
# steep increase in tolerance by intersection
#######################################################################

restore [file join [file dirname [info script]] bug25385_shell2.brep] s


plane p 28.5 0 0 1 0 0 0 1 0
mkface f p

puts TOL_BEFORE_DUMP; puts [dump s]
bop s f
puts TOL_AFTER_DUMP; puts [dump s]; puts TOL_END_DUMP
bopsection r
copy r result
puts [nbshapes result]
puts [checkshape result]
puts [vprops result]
puts [lprops result]



puts SCREEN_DONE

