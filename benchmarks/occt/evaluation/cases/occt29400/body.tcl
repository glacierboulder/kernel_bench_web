pload MODELING
set ::assets29400 [file join [file dirname [info script]] assets]
proc check_case {mode} {
    if {$mode eq "control"} {
        vertex a -1 0 0
        vertex b 1 0 0
        vertex c 0 -1 0
        vertex d 0 1 0
        edge e1 a b
        edge e2 c d
        compound e1 e2 input
        lassign {5 4 4} wantedV wantedE wantedL
    } else {
        restore [file join $::assets29400 bug29400_edges.brep] input
        if {$mode eq "translated"} {ttranslate input 1 2 -4}
        if {$mode eq "alternate"} {trotate input 0 0 0 0 0 1 90}
        lassign {3 2 1.78839} wantedV wantedE wantedL
    }
    bclearobjects
    bcleartools
    baddcompound input
    bfillds
    bbuild result
    set stats [nbshapes result]
    if {![regexp -line {^\s*VERTEX\s*:\s*(\d+)} $stats _ nv] ||
        ![regexp -line {^\s*EDGE\s*:\s*(\d+)} $stats _ ne] ||
        ![regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops result] _ total]} {error "missing geometry measurement"}
    set valid [string match {*This shape seems to be valid*} [checkshape result]]
    set bop [bopcheck result]
    set clean [string equal [string trim $bop] "This shape seems to be OK."]
    if {!$clean && ![regexp {V/V:} $bop]} {error "unexpected interference report: $bop"}
    puts "mode=$mode vertices=$nv edges=$ne length=$total valid=$valid self_check={$bop}"
    return [expr {$valid && $clean && $nv == $wantedV && $ne == $wantedE && abs($total-$wantedL)<0.00002}]
}
