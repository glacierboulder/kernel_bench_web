puts {=== OCCT 23998 public reproduction ===}
set inputs [file join [file dirname [info script]] inputs]
if {![file isdirectory $inputs]} {set inputs [file dirname [info script]]}
pload MODELING
restore [file join $inputs bug23998_draw.brep] b
explode b
bop b_1 b_2
bopsection result
puts [checkshape result]
puts [nbshapes result]
puts [lprops result]

puts PUBLIC_REPRO_COMPLETE
