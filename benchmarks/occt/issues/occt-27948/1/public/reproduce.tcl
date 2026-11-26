if {[catch {
    pload MODELING
    set here [file dirname [file normalize [info script]]]
    restore [file join $here bug27948_a.brep] a
    restore [file join $here bug27948_b.brep] b
    bcut result a b
    if {![isdraw result]} {error "no result"}
    puts [checkshape result]
    puts [nbshapes result]
    puts "AREA_MM2 [sprops result 1.e-6]"
    puts "VOLUME_MM3 [vprops result 1.e-6]"
} why]} {puts stderr "ERROR: $why"; exit 2}
exit 0
