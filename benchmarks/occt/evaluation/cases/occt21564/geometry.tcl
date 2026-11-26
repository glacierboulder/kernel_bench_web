pload MODELING
proc section_trial {mode} {
    global pa ta sa fa pb fb result
    if {$mode eq "control"} {
        psphere fa 4
        plane pb 0 0 0 0 0 1
        mkface fb pb -10 10 -10 10
        bsection result fa fb
        set length -1
        regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops result] _ length
        set e [llength [explode result e]]
        set valid [string match {*seems to be valid*} [checkshape result]]
        puts "mode=control edges=$e length=$length valid=$valid"
        return [expr {$valid && $e == 1 && abs($length-8*acos(-1))<0.001}]
    }
    plane pa 0 0 0 0 0 1
    trim ta pa -10 10 -10 10
    convert sa ta
    mkface fa sa
    if {$mode eq "translated"} {ttranslate fa 3 4 5}
    set ok 1
    foreach {ny extent expected} {0 10 20.0 2 15 22.360679775} {
        plane pb 0 0 0 1 $ny 0
        mkface fb pb -$extent $extent -$extent $extent
        if {$mode eq "translated"} {ttranslate fb 3 4 5}
        foreach approx {0 1} {
            set pair {fa fb}
            if {$mode eq "swapped"} {set pair {fb fa}}
            set args {}
            if {$approx} {set args {-a}}
            bsection result {*}$pair {*}$args
            set poles -1
            set length -1
            regexp {([0-9]+) Poles} [dump result] _ poles
            regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops result] _ length
            set edges [llength [explode result e]]
            set valid [string match {*seems to be valid*} [checkshape result]]
            puts "mode=$mode tilt=$ny approx=$approx edges=$edges poles=$poles length=$length valid=$valid"
            if {$edges != 1 || !$valid || $poles != 2 || abs($length-$expected)>0.001} {set ok 0}
        }
    }
    return $ok
}
