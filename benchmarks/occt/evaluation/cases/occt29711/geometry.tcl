proc measure_trial {tag assets} {
    pload MODELING
    restore [file join $assets CTO900_pro10658a.rle] a
    restore [file join $assets pro10658b.rle] b
    if {$tag eq "translated"} {ttranslate a b 6 -4 3}
    if {$tag eq "rotated"} {trotate a b 0 0 0 0 0 1 19}
    if {$tag eq "control"} {
        box a 4 3 2
        box b 2 0 0 4 3 2
    }
    if {$tag eq "swapped"} {bfuse r b a} else {bfuse r a b}
    set c [nbshapes r]
    set valid [checkshape r]
    foreach kind {WIRE FACE SHELL SOLID} {regexp "$kind\\s*:\\s*(\\d+)" $c _ count($kind)}
    regexp -nocase {Mass\s*:\s*([-+0-9.eE]+)} [sprops r] _ area
    regexp -nocase {Mass\s*:\s*([-+0-9.eE]+)} [vprops r] _ volume
    puts "MEASURE tag=$tag wire=$count(WIRE) face=$count(FACE) shell=$count(SHELL) solid=$count(SOLID) area=$area volume=$volume valid=$valid"
    if {$tag eq "control"} { set w 14; set f 14; set a0 72; set v0 36 } else { set w 9; set f 9; set a0 8231.06; set v0 30472.5 }
    return [expr {[string match "*seems to be valid*" $valid] && $count(WIRE)==$w && $count(FACE)==$f && $count(SHELL)==1 && $count(SOLID)==1 && abs($area-$a0)<0.02 && abs($volume-$v0)<0.12}]
}
