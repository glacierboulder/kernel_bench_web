pload MODELING
foreach thickness {0.00002 0.00003 0.00004 0.00005 0.0001} {
 puts "THICKNESS $thickness"
 pcylinder outer 200 100 [expr {900/acos(-1)}]
 pcylinder inner [expr {200-$thickness}] 100 [expr {900/acos(-1)}]
 bcut result outer inner
 puts [nbshapes result]
 puts [checkshape result]
 puts [vprops result]

if {![regexp -line {^\s*SOLID\s*:\s*1\s*$} [nbshapes result]]} {error "wrong topology"}
if {![string match "*This shape seems to be valid*" [checkshape result]]} {error "invalid shape"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [vprops result] full measured]} {error "missing measure"}
if {abs($measured-(250.0*$thickness*(400.0-$thickness)))>5e-05} {error "unexpected measure $measured"}

}


puts CASE_PASS
