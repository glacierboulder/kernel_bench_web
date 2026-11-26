pload MODELING
set here [file dirname [info script]]
foreach mode {original translated rotated control} {
    restore [file join $here assets bug25994_body.brep] body
    restore [file join $here assets bug25994_wing.brep] wing
    if {$mode eq "translated"} { ttranslate body wing -2 6 3 }
    if {$mode eq "rotated"} { trotate body wing 0 0 0 0 0 1 19 }
    if {$mode eq "control"} {box body 4 3 2; box wing 2 1 1 4 3 2}
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
    puts "MEASURE tag=$mode vertices=$v edges=$e length=$length maxTolerance=$tol"
    puts [checksection sect]
    bbop fused 1
    puts "FUSE $mode [nbshapes fused] [checkshape fused]"
}
