pload MODELING
restore [file join [file dirname [file normalize [info script]]] corner.brep] a
explode a E
if {[catch {fillet r a 0.01 a_1} why]} {
    puts "Fillet did not produce a result: $why"
} else {
    puts [checkshape r]
    puts [sprops r]
    puts "faces=[llength [explode r F]]"
}
exit
