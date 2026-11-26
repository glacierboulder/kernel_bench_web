pload MODELING
plane p 0 0 0 0 0 1
trim t p -10 10 -10 10
convert s t
mkface a s
foreach {ny extent} {0 10 2 15} {
    plane q 0 0 0 1 $ny 0
    mkface b q -$extent $extent -$extent $extent
    foreach approx {0 1} {
        set flags {}
        if {$approx} {set flags {-a}}
        bsection r a b {*}$flags
        set poles -1
        set length -1
        regexp {([0-9]+) Poles} [dump r] _ poles
        regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops r] _ length
        set valid [string match {*seems to be valid*} [checkshape r]]
        puts "tilt=$ny approx=$approx edges=[llength [explode r e]] poles=$poles length=$length valid=$valid"
    }
}
exit
