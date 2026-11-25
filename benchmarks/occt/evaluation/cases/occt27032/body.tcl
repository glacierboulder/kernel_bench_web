pload MODELING
set asset27032 [file join [file dirname [info script]] assets OCC27032_sh.brep]

proc check_case {mode} {
    global shapes shapes_1 shapes_2 cross result asset27032
    if {$mode eq "control"} {
        box shapes_1 10 10 10
        box shapes_2 5 5 5 10 10 10
    } else {
        restore $asset27032 shapes
        explode shapes
        if {$mode eq "translated"} {ttranslate shapes_1 shapes_2 0 0 20}
    }
    if {$mode eq "alternate"} {
        bsection cross shapes_2 shapes_1
    } else {
        bsection cross shapes_1 shapes_2
    }
    set counts [list [llength [explode cross e]] [llength [explode cross v]]]
    set section -1
    regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops cross] _ section
    set pieces {}
    foreach edge [explode cross e] {
        set el -1
        regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops $edge] _ el
        lappend pieces $el
    }
    bcut result shapes_1 shapes_2
    set valid [string match {*seems to be valid*} [checkshape result]]
    set area -1
    regexp {Mass\s*:\s*([-+0-9.eE]+)} [sprops result] _ area
    set target [expr {$mode eq "control" ? 600 : 1809490}]
    set expected [expr {$mode eq "control" ? "6 6" : "4 4"}]
    set targetLength [expr {$mode eq "control" ? 30 : 3606.37}]
    set ok [expr {$valid && $counts eq $expected && abs($section-$targetLength)<0.04 && abs($area-$target)<10}]
    puts "mode=$mode section_counts={$counts} section_length=$section piece_lengths={$pieces} area=$area valid=$valid verdict=[expr {$ok ? {pass} : {fail}}]"
    return $ok
}
