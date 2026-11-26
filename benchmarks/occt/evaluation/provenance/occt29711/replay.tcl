pload MODELING
set here [file dirname [info script]]
foreach tag {original translated rotated swapped control} {
    restore [file join $here assets CTO900_pro10658a.rle] a
    restore [file join $here assets pro10658b.rle] b
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
}
