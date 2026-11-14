pload MODELING
puts "========"
puts "OCC28274"
puts "========"
puts ""
######################################################
# BOPAlgo_MakerVolume fails to create solid
######################################################

restore [file join [file dirname [info script]] bug28274_tmp.brep] a

bnondestructive 1

set Log [eval mkvolume result [explode a f] ]
puts [nbshapes result]
puts [checkshape result]
puts [vprops result]
puts [lprops result]


if {![regexp -line {^\s*SOLID\s*:\s*3\s*$} [nbshapes result]]} {error "wrong topology"}
if {![string match "*This shape seems to be valid*" [checkshape result]]} {error "invalid result"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [vprops result] match measured]} {error "missing measure"}
if {abs($measured-741.787)>0.02} {error "unexpected measure"}
puts CASE_PASS
