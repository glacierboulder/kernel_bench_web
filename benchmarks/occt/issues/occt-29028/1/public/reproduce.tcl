pload MODELING
puts "============"
puts "OCC27079"
puts "============"
puts ""
##################################################################
# Bad approximation of intersection curves with variable curvature
##################################################################

restore [file join [file dirname [info script]] bug27079_s3.draw] s3
restore [file join [file dirname [info script]] bug27079_s4.draw] s4
trim  ts3 s3 pi-pi/30 pi -5 -2
mkface f1 ts3
mkface f2 s4


bop f1 f2
bopsection result
puts [nbshapes result]
puts [checkshape result]
puts [vprops result]
puts [lprops result]


puts PUBLIC_REPRO_COMPLETE
