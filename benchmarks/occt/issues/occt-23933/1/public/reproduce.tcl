puts {=== OCCT 23933 public reproduction ===}
set inputs [file join [file dirname [info script]] inputs]
if {![file isdirectory $inputs]} {set inputs [file dirname [info script]]}
pload MODELING
restore [file join $inputs bug23933_a.brep] a
restore [file join $inputs bug23933_b.brep] b
puts [checkshape a]
puts [checkshape b]
puts [bopargcheck a b -F]
bfuse result a b
puts [checkshape result]
puts [bopargcheck result]
puts [bopcheck result]

puts PUBLIC_REPRO_COMPLETE
