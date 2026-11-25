pload MODELING
set assets_32578 [file join [file dirname [info script]] assets]

proc check_case {mode} {
    global assets_32578
    if {$mode eq "control"} {
        plane surface 0 0 0 0 0 1
        mkface f surface 0 10 0 10
        vertex a -1 4 0
        vertex b 11 4 0
        edge stroke a b
        set tools [list stroke]
        set expectedCounts {6 7 2 2}
        set expectedArea 100.0
    } else {
        restore [file join $assets_32578 bug32578_face.brep] f
        restore [file join $assets_32578 bug32578_edges.brep] ce
        if {$mode eq "translated"} {
            ttranslate f 12 -8 4
            ttranslate ce 12 -8 4
        }
        set tools [explode ce]
        if {$mode eq "alternate"} {set tools [lreverse $tools]}
        set expectedCounts {646 1234 589 589}
        set expectedArea 351.033
    }
    bfuzzyvalue 0.01
    bclearobjects
    bcleartools
    baddobjects f
    baddtools {*}$tools
    bfillds
    set report [bsplit result]
    if {![isdraw result]} {
        puts "$mode missing_result=1 splitter_report=$report"
        return 0
    }

    set valid [string match {*This shape seems to be valid*} [checkshape result]]
    set interferenceFree [string match {*This shape seems to be OK*} [bopcheck result]]
    set stats [nbshapes result -t]
    set counts {}
    foreach kind {VERTEX EDGE WIRE FACE} {
        if {![regexp -line [format {^\s*%s\s*:\s*([0-9]+)} $kind] $stats _ n]} {
            error "missing $kind count"
        }
        lappend counts $n
    }
    if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [sprops result 1.e-4] _ area]} {
        error "missing area"
    }
    puts "$mode valid=$valid interferenceFree=$interferenceFree counts=$counts area=$area"
    return [expr {$valid && $interferenceFree && $counts eq $expectedCounts &&
                  abs($area - $expectedArea) < 0.015}]
}
