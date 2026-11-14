pload MODELING
puts "============"
puts "OCC17194"
puts "============"
puts ""
#######################################################################
# Incorrect section of a face got by extrusion of an arc of circle
#######################################################################

set BugNumber OCC17194

circle f 0 0 0 0 0 1 1 0 0 20
mkedge f f -pi/2 pi/2
prism f f 50 0 30
plane pl 10 0 0 1 0 4
mkface pl pl
bsection result f pl

puts [nbshapes result]
puts [lprops result]
puts [checkshape result]


if {![regexp -line {^\s*EDGE\s*:\s*2\s*$} [nbshapes result]]} {error "wrong topology"}
if {![string match "*This shape seems to be valid*" [checkshape result]]} {error "invalid shape"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops result] full measured]} {error "missing measure"}
if {abs($measured-(15.8064))>0.001} {error "unexpected measure $measured"}

pload MODELING
puts "============"
puts "OCC17194"
puts "============"
puts ""
#######################################################################
# Incorrect section of a face got by extrusion of an arc of circle
#######################################################################

set BugNumber OCC17194

circle f 0 0 0 0 0 1 1 0 0 20
mkedge f f -pi/2 pi/2
prism f f 50 0 30
plane pl 10 0 10 1 0 4
mkface pl pl
bsection result f pl

puts [nbshapes result]
puts [lprops result]
puts [checkshape result]


if {![regexp -line {^\s*EDGE\s*:\s*1\s*$} [nbshapes result]]} {error "wrong topology"}
if {![string match "*This shape seems to be valid*" [checkshape result]]} {error "invalid shape"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops result] full measured]} {error "missing measure"}
if {abs($measured-(54.6122))>0.001} {error "unexpected measure $measured"}

puts CASE_PASS
