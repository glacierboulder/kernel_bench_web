pload MODELING

proc check_case {mode} {
    global line1 line2 e1 e2 v1 v2 result
    set scale [expr {$mode eq "alternate" ? 3.0 : 1.0}]
    set len [expr {10.0 * $scale}]
    set tol [expr {0.25 * $scale}]
    set gap [expr {$mode eq "control" ? 2.0 : 2 * $tol}]
    lassign {0.0 0.0 0.0} x y z
    if {$mode eq "translated"} { lassign {13.0 -17.0 3.0} x y z }
    line line1 $x $y $z 0 0 1
    mkedge e1 line1 0 $len
    line line2 $x [expr {$y + $gap}] $z 0 0 1
    mkedge e2 line2 0 $len
    vertex v1 $x [expr {$y + $gap / 2.0}] $z
    settolerance v1 $tol
    vertex v2 $x [expr {$y + $gap / 2.0}] [expr {$z + $len}]
    settolerance v2 $tol

    boptions -default
    bclearobjects
    bcleartools
    baddobjects e1 e2 v1 v2
    bfillds
    bbuild result
    set stats [nbshapes result]
    set props [lprops result]
    set valid [string match {*seems to be valid*} [checkshape result]]
    set readVertices [regexp {(?m)^\s*VERTEX\s*:\s*([0-9]+)\s*$} $stats _ vertices]
    set readEdges [regexp {(?m)^\s*EDGE\s*:\s*([0-9]+)\s*$} $stats _ edges]
    set readLength [regexp {Mass\s*:\s*([-+0-9.eE]+)} $props _ length]
    if {!$readVertices || !$readEdges || !$readLength} {
        error "missing vertex count, edge count, or total length"
    }
    set wantEdges [expr {$mode eq "control" ? 2 : 1}]
    set wantVertices [expr {$mode eq "control" ? 6 : 2}]
    set passed [expr {$valid &&
        $vertices == $wantVertices && $edges == $wantEdges &&
        abs($length - $wantEdges * $len) < 1e-6}]
    puts "mode=$mode vertices=$vertices edges=$edges length=$length valid=$valid verdict=[expr {$passed ? {pass} : {fail}}]"
    return $passed
}
