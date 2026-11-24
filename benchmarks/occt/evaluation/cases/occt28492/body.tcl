pload MODELING
set ::sectionAssets [file join [file dirname [info script]] assets]

proc check_case {mode} {
    global f1 f2 planeCtr sec
    if {$mode eq "control"} {
        box f1 0 0 0 10 10 10
        plane planeCtr 0 0 5 0 0 1
        mkface f2 planeCtr -15 15 -15 15
        set reference {10 10 10 10}
        set vertices 4
    } else {
        restore [file join $::sectionAssets a350.brep] f1
        restore [file join $::sectionAssets b350.brep] f2
        if {$mode eq "translated"} {ttranslate f1 f2 1 -2 3}
        if {$mode eq "alternate"} {trotate f1 f2 0 0 0 0 0 1 15}
        set reference {0.63425 0.63425 0.65 0.65 0.66655 0.66655 0.67596 0.67596 1.23207 1.23207 1.23997 1.23997 1.3 1.33289 1.33289 2.04206 5.73109 5.73109}
        set vertices 16
    }
    bsection sec f1 f2
    set lengths {}
    foreach edge [explode sec e] {
        if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops $edge] _ length]} {
            error "Section edge length unavailable"
        }
        lappend lengths $length
    }
    set lengths [lsort -real $lengths]
    set nVertices [llength [explode sec v]]
    set valid [string match {*seems to be valid*} [checkshape sec]]
    set passing [expr {$valid && $nVertices==$vertices && [llength $lengths]==[llength $reference]}]
    if {$passing} {
        foreach actual $lengths expected $reference {
            if {abs($actual-$expected)>0.001} {set passing 0}
        }
    }
    puts "mode=$mode vertices=$nVertices lengths={$lengths} valid=$valid verdict=[expr {$passing ? {pass} : {fail}}]"
    return $passing
}
