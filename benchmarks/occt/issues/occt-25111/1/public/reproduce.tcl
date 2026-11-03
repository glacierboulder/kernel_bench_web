pload TOPTEST
restore [file join [file dirname [info script]] bug25111_s1.draw] s1
restore [file join [file dirname [info script]] bug25111_s2.draw] s2
mkface f1 s1
mkface f2 s2
bop f1 f2
bopsection result
checkshape result
checksection result
lprops result
