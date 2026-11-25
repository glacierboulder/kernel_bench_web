pload MODELING

proc count_27274 {stats kind} {
    set pattern [format {^\s*%s\s*:\s*([0-9]+)} $kind]
    if {![regexp -line $pattern $stats _ count]} {
        error "missing $kind count"
    }
    return $count
}

proc check_case {mode} {
    set scale 1.0
    set radius [expr {50 * $scale}]
    set height [expr {145 * $scale}]
    pcylinder b1 $radius $height
    tcopy b1 b2
    trotate b2 0 0 0 1 0 0 45
    if {$mode eq "translated"} {
        ttranslate b1 17 -29 35
        ttranslate b2 17 -29 35
    } elseif {$mode eq "alternate"} {
        trotate b1 0 0 0 0 0 1 23
        trotate b2 0 0 0 0 0 1 23
    } elseif {$mode eq "control"} {
        ttranslate b2 300 0 0
    }

    bclearobjects
    bcleartools
    baddobjects b1
    baddtools b2
    bfillds
    bbuild result

    set valid [string match {*This shape seems to be valid*} [checkshape result]]
    set stats [nbshapes result -t]
    set solids [count_27274 $stats SOLID]
    set faces [count_27274 $stats FACE]
    set edges [count_27274 $stats EDGE]
    set vertices [count_27274 $stats VERTEX]
    if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [sprops result 1.0e-4] _ area]} {
        error "missing surface area"
    }
    if {$mode eq "control"} {
        set expected [expr {4 * acos(-1) * $radius * ($height + $radius)}]
        set expectedCounts {2 6 6 4}
    } else {
        set expected [expr {154518 * $scale * $scale}]
        set expectedCounts {3 10 11 5}
    }
    puts "$mode valid=$valid solids=$solids faces=$faces edges=$edges vertices=$vertices area=$area expected=$expected"
    return [expr {$valid && [list $solids $faces $edges $vertices] eq $expectedCounts
                  && abs($area - $expected) <= 3 * $scale * $scale}]
}
