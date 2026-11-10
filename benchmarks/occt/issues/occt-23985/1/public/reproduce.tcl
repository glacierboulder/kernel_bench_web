puts {=== OCCT 23985 public reproduction ===}
set inputs [file join [file dirname [info script]] inputs]
if {![file isdirectory $inputs]} {set inputs [file dirname [info script]]}
pload MODELING
restore [file join $inputs bug23985_b1_draw.brep] a
restore [file join $inputs bug23985_b2_draw.brep] b

bsection result a b
puts [checkshape result]
puts [nbshapes result]
puts [lprops result]


puts PUBLIC_REPRO_COMPLETE
