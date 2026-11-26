pload MODELING
set assets [file dirname [info script]]
set tag original
    restore [file join $assets bug27615.brep] body
    explode body f
    copy body_1 f1
    copy body_19 f2
    bsection sectionResult f1 f2
    set topo [nbshapes sectionResult]
    regexp {VERTEX\s*:\s*([0-9]+)} $topo _ nv
    regexp {EDGE\s*:\s*([0-9]+)} $topo _ ne
    regexp -nocase {mass\s*:\s*([-+0-9.eE]+)} [lprops sectionResult] _ length
    regexp {Tolerance MAX=([-+0-9.eE]+)} [tolerance sectionResult] _ tol
    puts "MEASURE tag=$tag vertices=$nv edges=$ne length=$length maxTolerance=$tol"
