pload MODELING
box a 10 10 10
plane plane1 0 0 5 0 0 1
mkface b plane1
bsection result a b
if {![regexp -line {^\s*EDGE\s*:\s*4\s*$} [nbshapes result]]} {error "regression edge count"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops result] full value] || abs($value-40)>1e-6} {error "regression length"}
puts TEST_DONE
