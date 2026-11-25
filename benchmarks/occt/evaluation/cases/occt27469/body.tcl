pload MODELING
proc check_case {mode} {
    set height 0.1
    if {$mode eq "alternate"} {set height 0.01}
    if {$mode eq "control"} {set height 0}
    set poles {}
    for {set i 0} {$i <= 24} {incr i} {
        lappend poles $i 0 [expr {$i == 23 ? $height : 0}]
    }
    beziercurve c 25 {*}$poles
    mkedge lifted c
    plane p 0 0 0 0 0 1
    mkface sheet p -5 30 -5 5
    if {$mode eq "translated"} {
        ttranslate lifted 10 -2 4
        ttranslate sheet 10 -2 4
    }
    bcommon result lifted sheet
    if {![regexp {EDGE\s*:\s*([0-9]+)} [nbshapes result] _ edges] ||
        ![regexp {Mass\s*:\s*([0-9.eE+-]+)} [lprops result] _ length]} {
        error "missing common edge count or length"
    }
    puts "$mode height=$height commonEdges=$edges commonLength=$length"
    if {$mode eq "control"} {return [expr {$edges == 1 && abs($length-24) < 1e-6}]}
    return [expr {$edges == 0 && abs($length) < 1e-6}]
}
