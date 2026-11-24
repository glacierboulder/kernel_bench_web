pload MODELING
proc check_case {mode} {
    set depth 0.005
    set xOffset 0
    if {$mode eq "translated"} {set xOffset 3}
    if {$mode eq "alternate"} {set depth 0.001}
    if {$mode eq "control"} {set depth 0.05}
    set outer [expr {1-$depth}]
    set inner [expr {-1-$depth}]
    beziercurve parab 3 -10 0 $outer 0 0 $inner 10 0 $outer
    mkedge e parab
    settolerance e 0.01
    plane p 0 0 0 0 0 1
    mkface f p -20 20 -20 20
    if {$xOffset != 0} {
        ttranslate e $xOffset 0 0
        ttranslate f $xOffset 0 0
    }
    bclearobjects
    bcleartools
    baddobjects e
    baddtools f
    bfillds
    set interferences [bopinterf e f]
    if {![string match {*E/F:*} $interferences]} {error "missing E/F interference report"}
    set newVertices [bopnews v]
    set xs {}
    set inPlane 1
    foreach v $newVertices {
        mkpoint pos $v
        coord pos px py pz
        lappend xs [dval px]
        if {abs([dval py]) > 1e-6 || abs([dval pz]) > 1e-6} {set inPlane 0}
    }
    set xs [lsort -real $xs]
    set points [regexp -all {\([0-9]+, [0-9]+, [0-9]+\)} $interferences]
    puts "$mode depth=$depth interferencePoints=$points x=$xs inPlane=$inPlane"
    if {$points != 2 || [llength $xs] != 2} {return 0}
    set root [expr {10*sqrt($depth)}]
    return [expr {$inPlane && abs([lindex $xs 0] - ($xOffset-$root)) < 1e-6 &&
                  abs([lindex $xs 1] - ($xOffset+$root)) < 1e-6}]
}
