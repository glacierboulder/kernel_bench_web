puts {=== OCCT 25337 public reproduction ===}
set inputs [file join [file dirname [info script]] inputs]
if {![file isdirectory $inputs]} {set inputs [file dirname [info script]]}
pload MODELING
circle c1 -50 0 0 10
circle c2 -35 0 0 10
mkedge e1 c1
mkedge e2 c2
wire w1 e1
wire w2 e2
mkplane f1 w1
mkplane f2 w2
bop f1 f2
bopfuse fused
bopcommon common
puts "=== FUSED ==="
puts [checkshape fused]
puts [sprops fused]
puts [nbshapes fused]
puts "=== COMMON ==="
puts [checkshape common]
puts [sprops common]
puts [nbshapes common]


puts PUBLIC_REPRO_COMPLETE
