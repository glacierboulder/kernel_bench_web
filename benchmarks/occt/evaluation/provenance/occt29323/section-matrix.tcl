pload MODELING
set assets [file join [file dirname [info script]] assets]
foreach tag {original translated rotated control} {
    if {$tag eq "control"} {
        plane p 0 0 0 0 0 1
        mkface f1 p -5 5 -3 3
        plane q 0 0 0 1 0 0
        mkface f2 q -15 15 -15 15
        set expected 6.0
    } else {
        restore [file join $assets bug27615.brep] body
        explode body f
        copy body_1 f1
        copy body_19 f2
        if {$tag eq "translated"} {ttranslate f1 f2 6 -4 3}
        if {$tag eq "rotated"} {trotate f1 f2 0 0 0 0 0 1 19}
        set expected 1.93162
    }
    bsection sectionResult f1 f2
    set topo [nbshapes sectionResult]
    regexp {VERTEX\s*:\s*([0-9]+)} $topo _ nv
    regexp {EDGE\s*:\s*([0-9]+)} $topo _ ne
    regexp -nocase {mass\s*:\s*([-+0-9.eE]+)} [lprops sectionResult] _ length
    regexp {Tolerance MAX=([-+0-9.eE]+)} [tolerance sectionResult] _ tol
    puts "MEASURE tag=$tag vertices=$nv edges=$ne length=$length maxTolerance=$tol"
}
