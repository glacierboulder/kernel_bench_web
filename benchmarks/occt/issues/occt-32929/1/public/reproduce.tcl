set here [file dirname [info script]]
set model [file join $here inputs bug32929.brep]
if {![file isfile $model]} {set model [file join $here bug32929.brep]}
pload MODELING
restore $model b
explode b E
puts START_BLEND
blend result b 1 b_8
puts END_BLEND
puts [checkshape result]
puts [nbshapes result]
puts [sprops result 1e-5]
puts PUBLIC_REPRO_COMPLETE
