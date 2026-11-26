proc measure_trial {tag assets} {
    pload MODELING
    restore [file join $assets bug25994_body.brep] body
    restore [file join $assets bug25994_wing.brep] wing
    if {$tag eq "translated"} { ttranslate body wing -2 6 3 }
    if {$tag eq "rotated"} { trotate body wing 0 0 0 0 0 1 19 }
    if {$tag eq "control"} {box body 4 3 2; box wing 2 1 1 4 3 2}
    bclearobjects
    bcleartools
    baddobjects body
    baddtools wing
    bfillds
    bbop sect 4
    set counts [nbshapes sect]
    regexp {VERTEX\s*:\s*([0-9]+)} $counts _ v
    regexp {EDGE\s*:\s*([0-9]+)} $counts _ e
    regexp {Tolerance MAX=([-+0-9.eE]+)} [tolerance sect] _ tol
    regexp -nocase {mass\s*:\s*([-+0-9.eE]+)} [lprops sect] _ length
    regexp {nb alone Vertices\s*:\s*([0-9]+)} [checksection sect] _ alone
    puts "MEASURE tag=$tag vertices=$v edges=$e length=$length maxTolerance=$tol"
    puts "ALONE=$alone"
    if {$tag eq "control"} {set nb 6; set expected 10.0} else {set nb 3; set expected 620.026}
    return [expr {$v==$nb && $e==$nb && $alone==0 && abs($length-$expected)<0.001 && $tol<0.00005}]
}
