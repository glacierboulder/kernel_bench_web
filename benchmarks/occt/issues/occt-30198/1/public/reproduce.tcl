puts {=== OCCT 30198 public reproduction ===}
set inputs [file join [file dirname [info script]] inputs]
if {![file isdirectory $inputs]} {set inputs [file dirname [info script]]}
pload MODELING
restore [file join $inputs bug30198_src.brep] a
restore [file join $inputs bug30198_tool.brep] b
puts OPERATION_STARTED
bfuse result a b
puts ===RESULT===
puts [checkshape result]
puts [nbshapes result]
puts [vprops result 1e-5]
puts [sprops result 1e-5]


puts PUBLIC_REPRO_COMPLETE
