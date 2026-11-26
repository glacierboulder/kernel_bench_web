proc section_trial {mode assets} {
    pload MODELING
    set locations {original 183.60 left 183.59 right 183.61}
    set lengths {original 0.000510151 left 0.00046535 right 0.000557059}
    if {$mode eq "control"} {
        plane surfA 0 0 0 0 0 1
        mkface faceA surfA -5 5 -3 3
        plane surfB 0 0 0 1 0 0
        mkface faceB surfB -15 15 -15 15
        set length 6.0
    } else {
        restore [file join $assets bug24094_face.brep] faceA
        plane surfB [dict get $locations $mode] 0 0 1 0 0 0 1 0
        mkface faceB surfB
        set length [dict get $lengths $mode]
    }
    foreach {name flags} {standard {} first-only {-n2d2}} {
        bsection result faceA faceB {*}$flags
        set counts [nbshapes result]
        if {![regexp {VERTEX\s*:\s*([0-9]+)} $counts _ v] || ![regexp {EDGE\s*:\s*([0-9]+)} $counts _ e]} { error "Unrecognized topology" }
        if {![regexp -nocase {mass\s*[:=]\s*([-+0-9.eE]+)} [lprops result] _ measured]} { error "Missing length" }
        puts "case=$mode mode=$name vertices=$v edges=$e length=$measured"
        set tol [expr {$length*1.e-4 > 1.e-8 ? $length*1.e-4 : 1.e-8}]
        if {$v != 2 || $e != 1 || abs($measured-$length) > $tol} {return 0}
    }
    return 1
}
