pload MODELING
set tag original
set assets [file dirname [info script]]
    restore [file join $assets bug25994_body.brep] body
    restore [file join $assets bug25994_wing.brep] wing
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
