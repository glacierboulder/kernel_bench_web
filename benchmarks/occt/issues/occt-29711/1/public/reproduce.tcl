pload MODELING
set here [file dirname [info script]]
foreach tag {original} {
    restore [file join $here CTO900_pro10658a.rle] a
    restore [file join $here pro10658b.rle] b
    bfuse r a b
    set c [nbshapes r]
    set valid [checkshape r]
    foreach kind {WIRE FACE SHELL SOLID} {regexp "$kind\\s*:\\s*(\\d+)" $c _ count($kind)}
    regexp -nocase {Mass\s*:\s*([-+0-9.eE]+)} [sprops r] _ area
    regexp -nocase {Mass\s*:\s*([-+0-9.eE]+)} [vprops r] _ volume
    puts "MEASURE tag=$tag wire=$count(WIRE) face=$count(FACE) shell=$count(SHELL) solid=$count(SOLID) area=$area volume=$volume valid=$valid"
}
