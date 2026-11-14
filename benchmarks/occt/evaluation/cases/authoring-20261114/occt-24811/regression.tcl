pload MODELING
vertex v1 -2 0 0
vertex v2 2 0 0
vertex v3 0 -2 0
vertex v4 0 2 0
edge a v1 v2
edge b v3 v4
bop a b
bopcut result
if {![regexp -line {^\s*EDGE\s*:\s*2\s*$} [nbshapes result]]} {error "regression edge count"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops result] full value] || abs($value-4)>1e-6} {error "regression length"}
puts TEST_DONE
