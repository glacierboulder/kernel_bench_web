puts {=== OCCT 29038 public reproduction ===}
set inputs [file join [file dirname [info script]] inputs]
if {![file isdirectory $inputs]} {set inputs [file dirname [info script]]}
pload MODELING
restore [file join $inputs bug29038_bfuse_hang.brep] a
explode a
puts OPERATION_STARTED
bfuse result a_1 a_2
puts ===RESULT===
puts [checkshape result]
puts [nbshapes result]
puts {=== surface area (open faces; NOT volume) ===}
puts [sprops result 1e-5]
puts [lprops result]


puts PUBLIC_REPRO_COMPLETE
