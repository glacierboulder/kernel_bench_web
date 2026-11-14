pload MODELING
puts "============"
puts "OCC12507"
puts "============"
puts ""
#######################################################################
# Wrong result of fuse operation
#######################################################################

puts "First shape ..."
pcylinder c 3 3
explode c e

puts "Second shape ..."
tcopy c_3 e3
ttranslate e3 0 6 0

bop c_3 e3
bopfuse result

puts [nbshapes result]
puts [lprops result]
puts [checkshape result]


if {![regexp -line {^\s*EDGE\s*:\s*4\s*$} [nbshapes result]]} {error "wrong topology"}
if {![string match "*This shape seems to be valid*" [checkshape result]]} {error "invalid shape"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops result] full measured]} {error "missing measure"}
if {abs($measured-(37.6991))>0.001} {error "unexpected measure $measured"}

puts CASE_PASS
if {![regexp -line {^\s*VERTEX\s*:\s*3\s*$} [nbshapes result]]} {error "missing tangent vertex"}
