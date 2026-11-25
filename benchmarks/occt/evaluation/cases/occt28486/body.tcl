pload MODELING

proc check_case {mode} {
    global planeA faceA faceB lineTool edgeTool result
    set halfTool [expr {$mode eq "alternate" ? 7.5 : 8.0}]
    plane planeA 0 0 0 0 0 1
    mkface faceA planeA -10 10 -10 10
    copy faceA faceB
    trotate faceB 0 0 0 1 0 0 20
    line lineTool 0 0 0 0 1 0
    mkedge edgeTool lineTool [expr {-$halfTool}] $halfTool
    trotate edgeTool 0 0 0 1 0 0 10
    settolerance edgeTool 1.5
    if {$mode eq "translated"} {
        ttranslate faceA faceB edgeTool 13 -7 4
    }
    if {$mode eq "control"} {
        ttranslate edgeTool 0 0 30
    }
    bclearobjects
    bcleartools
    baddobjects faceA faceB
    baddtools edgeTool
    bfillds
    bbuild result

    set valid [string match {*seems to be valid*} [checkshape result]]
    set faces [explode result f]
    set areas {}
    set wires {}
    set markedLengths {}
    set passed [expr {$valid && [llength $faces] == 4}]
    set expectedWires [expr {$mode eq "control" ? 1 : 2}]
    foreach face $faces {
        if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [sprops $face] _ area]} {
            error "Cannot measure $face"
        }
        set faceWires [explode $face w]
        set wireCount [llength $faceWires]
        set boundaryCount 0
        set markedCount 0
        foreach wire $faceWires {
            if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops $wire] _ length]} {
                error "Cannot measure $wire"
            }
            if {abs($length - 60.0) < 0.001} {
                incr boundaryCount
            } elseif {[llength [explode $wire e]] == 1 && abs($length - $halfTool) < 0.001} {
                incr markedCount
                lappend markedLengths $length
            }
        }
        lappend areas $area
        lappend wires $wireCount
        if {abs($area - 200.0) > 0.001 || $wireCount != $expectedWires
            || $boundaryCount != 1 || $markedCount != $expectedWires - 1} {
            set passed 0
        }
    }
    puts "mode=$mode faces=[llength $faces] areas={$areas} wires={$wires} markedLengths={$markedLengths} valid=$valid verdict=[expr {$passed ? {pass} : {fail}}]"
    return $passed
}
