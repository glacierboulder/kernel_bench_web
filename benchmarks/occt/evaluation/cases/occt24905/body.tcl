pload MODELING

proc count_24905 {stats kind} {
    set pattern [format {^\s*%s\s*:\s*([0-9]+)} $kind]
    if {![regexp -line $pattern $stats _ count]} {
        error "missing $kind count"
    }
    return $count
}

proc measure_24905 {output} {
    if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} $output _ mass]} {
        error "missing mass property"
    }
    return $mass
}

proc check_case {mode} {
    circle c1 0 0 0 0 -1 0 75
    circle c2 0 0 0 0 -1 0 65
    mkedge c1 c1
    mkedge c2 c2
    wire c1 c1
    wire c2 c2
    orientation c2 R
    mkplane f1 c1 1
    add c2 f1
    prism p1 f1 0 1000 0
    trotate p1 0 0 0 0 0 1 180
    circle c3 50 500 -2000 0 0 1 50
    mkedge c3 c3
    wire c3 c3
    mkplane f2 c3 1
    set toolLength [expr {$mode eq "alternate" ? 4500 : 4000}]
    prism p2 f2 0 0 $toolLength
    trotate p2 0 500 0 1 0 0 -77
    trotate p2 0 0 0 0 0 1 180

    if {$mode eq "translated"} {
        ttranslate p1 0 32 0
        ttranslate p2 0 32 0
    } elseif {$mode eq "control"} {
        ttranslate p2 500 0 0
    }

    bclearobjects
    bcleartools
    baddobjects p1
    baddtools p2
    bfillds
    bbop cutResult 2
    bbop sectionResult 4

    set valid [string match {*This shape seems to be valid*} [checkshape cutResult]]
    set cutCounts [nbshapes cutResult]
    set solids [count_24905 $cutCounts SOLID]
    set faces [count_24905 $cutCounts FACE]
    set volume [measure_24905 [vprops cutResult 1.0e-4]]
    set sectionCounts [nbshapes sectionResult]
    set edges [count_24905 $sectionCounts EDGE]
    set vertices [count_24905 $sectionCounts VERTEX]
    puts "$mode valid=$valid solids=$solids faces=$faces volume=$volume section_edges=$edges section_vertices=$vertices"
    if {$mode eq "control"} {
        set expected [expr {acos(-1) * (75 * 75 - 65 * 65) * 1000}]
        set inputFaces [count_24905 [nbshapes p1] FACE]
        return [expr {$valid && $solids == 1 && $faces == $inputFaces
                      && abs($volume - $expected) <= 50 && $edges == 0 && $vertices == 0}]
    }

    set sectionLength [measure_24905 [lprops sectionResult]]
    set sectionClosed [string match {*Section is OK*} [checksection sectionResult -r 0]]
    puts "$mode section_length=$sectionLength closed=$sectionClosed"
    return [expr {$valid && $solids == 1 && $faces == 7
                  && abs($volume - 3540410) <= 50
                  && $edges == 8 && $vertices == 8 && $sectionClosed
                  && abs($sectionLength - 3965.07) <= 0.2}]
}
