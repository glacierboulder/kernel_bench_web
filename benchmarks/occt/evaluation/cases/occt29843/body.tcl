pload MODELING
set input_29843 [file join [file dirname [info script]] assets bug29843_loc.brep]

proc check_case {mode} {
    global input_29843
    if {$mode eq "control"} {
        box left 0 0 0 6 5 4
        box right 3 1 1 8 7 6
        set expectedVolume 36
        set expectedFaces 6
    } else {
        restore $input_29843 s
        if {$mode eq "translated"} {ttranslate s 1 3 -2}
        explode s
        set expectedVolume 1176100
        set expectedFaces 5
    }
    if {$mode eq "control"} {
        set operands {left right}
    } elseif {$mode eq "alternate"} {
        set operands {s_2 s_1}
    } else {
        set operands {s_1 s_2}
    }
    bclearobjects
    bcleartools
    baddobjects [lindex $operands 0]
    baddtools [lindex $operands 1]
    bfillds
    bbop section 4
    set sectionStats [nbshapes section -t]
    if {![regexp {EDGE\s*:\s*([0-9]+)} $sectionStats _ sectionEdges] ||
        ![regexp {VERTEX\s*:\s*([0-9]+)} $sectionStats _ sectionVertices] ||
        ![regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops section] _ sectionLength]} {
        error "missing intersection geometry"
    }
    set expectedLength [expr {$mode eq "control" ? 20 : 952.189}]
    set expectedEdges [expr {$mode eq "control" ? 6 : 7}]
    set sectionOK [expr {$sectionEdges == $expectedEdges && $sectionVertices == 6 &&
                         abs($sectionLength - $expectedLength) < 0.01}]
    puts "$mode sectionEdges=$sectionEdges sectionVertices=$sectionVertices sectionLength=$sectionLength"
    set report [bbop result 0]
    if {![isdraw result] || [catch {checkshape result} shapeCheck]} {
        puts "$mode missing_result=1 common_report=$report"
        return 0
    }
    set valid [string match {*This shape seems to be valid*} $shapeCheck]
    set interferenceFree [string match {*This shape seems to be OK*} [bopcheck result]]
    set stats [nbshapes result -t]
    if {![regexp {FACE\s*:\s*([0-9]+)} $stats _ faces] ||
        ![regexp {SOLID\s*:\s*([0-9]+)} $stats _ solids] ||
        ![regexp {Mass\s*:\s*([-+0-9.eE]+)} [vprops result] _ volume]} {
        error "missing count or volume"
    }
    puts "$mode valid=$valid interferenceFree=$interferenceFree faces=$faces solids=$solids volume=$volume"
    return [expr {$sectionOK && $valid && $interferenceFree && $solids == 1 && $faces == $expectedFaces &&
                  abs($volume - $expectedVolume) <= 1.e-5 * $expectedVolume}]
}
