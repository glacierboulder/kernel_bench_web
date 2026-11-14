pload MODELING
puts "========="
puts "OCC26450"
puts "========="
puts ""
###########################################
# Boolean operation is running endless
###########################################


restore [file join [file dirname [info script]] bug26450_a.brep] a
restore [file join [file dirname [info script]] bug26450_b.brep] b

bop a b
bopsection result
puts [nbshapes result]
puts [checkshape result]
puts [vprops result]
puts [lprops result]


if {![regexp -line {^\s*EDGE\s*:\s*12\s*$} [nbshapes result]]} {error "wrong topology"}
if {![string match "*This shape seems to be valid*" [checkshape result]]} {error "invalid result"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops result] match measured]} {error "missing measure"}
if {abs($measured-941.75)>0.02} {error "unexpected measure"}
puts CASE_PASS
