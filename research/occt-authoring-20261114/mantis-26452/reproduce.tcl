pload MODELING
restore [file join [file dirname [info script]] bug26452_edges.brep] e
explode e
bclearobjects
bcleartools
baddobjects e_1 e_2
bfillds
bfuse r1 e_1 e_2
tcopy e_1 e1
tcopy e_2 e2
bfuse r2 e1 e2

if {![regexp -line {^\s*EDGE\s*:\s*2\s*$} [nbshapes r1]]} {error "unexpected topology"}
if {![string match "*This shape seems to be valid*" [checkshape r1]]} {error "invalid shape"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops r1] full measured] || abs($measured-78.3329)>0.002} {error "unexpected measure"}

if {![regexp -line {^\s*EDGE\s*:\s*2\s*$} [nbshapes r2]]} {error "unexpected topology"}
if {![string match "*This shape seems to be valid*" [checkshape r2]]} {error "invalid shape"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops r2] full measured] || abs($measured-78.3329)>0.002} {error "unexpected measure"}

puts CASE_PASS

