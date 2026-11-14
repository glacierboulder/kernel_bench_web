pload MODELING
box f1 10 10 10
plane p 0 0 5 0 0 1
mkface f2 p
bsection e f1 f2
puts [nbshapes e]
puts [checkshape e]
puts [lprops e]

if {![regexp -line {^\s*EDGE\s*:\s*4\s*$} [nbshapes e]]} {error "expected four edges"}
if {![string match "*This shape seems to be valid*" [checkshape e]]} {error "invalid section"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops e] match len] || abs($len-40)>0.001} {error "wrong length"}
puts TEST_DONE


