pload MODELING
set asset28690 [file join [file dirname [info script]] assets bug28690_m8_faces.brep]

proc check_case {mode} {
    global a f r asset28690
    set shift [expr {$mode eq "translated" ? 32.0 : 0.0}]
    if {$mode eq "control"} {
        box a -5 -5 -5 10 10 10
    } else {
        restore $asset28690 a
        ttranslate a [expr {-20000+$shift}] -584.41225425562368 0
    }
    plane f $shift 0 0 1 0 0
    mkface f f
    if {$mode eq "alternate"} {
        bsection r f a
    } else {
        bsection r a f
    }
    set vertices [llength [explode r v]]
    set edges [explode r e]
    set invalid 0
    foreach edge $edges {
        if {[string match {*no valid range*} [validrange $edge]]} {incr invalid}
    }
    set length -1
    regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops r] _ length
    set valid [string match {*seems to be valid*} [checkshape r]]
    set target [expr {$mode eq "control" ? 40.0 : 594.045}]
    set need [expr {$mode eq "control" ? 4 : 3}]
    set ok [expr {$valid && [llength $edges]==$need && $vertices==4 && !$invalid && abs($length-$target)<0.01}]
    puts "mode=$mode edges=[llength $edges] vertices=$vertices no_valid_range=$invalid length=$length valid=$valid verdict=[expr {$ok ? {pass} : {fail}}]"
    return $ok
}
