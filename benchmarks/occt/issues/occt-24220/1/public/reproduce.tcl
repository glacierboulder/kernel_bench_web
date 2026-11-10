puts {=== OCCT 24220 public reproduction ===}
set inputs [file join [file dirname [info script]] inputs]
if {![file isdirectory $inputs]} {set inputs [file dirname [info script]]}
pload MODELING
restore [file join $inputs bug24220_A.brep] result
puts OPERATION_STARTED
puts [bopargcheck result]


puts PUBLIC_REPRO_COMPLETE
