source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
restore [file join [file dirname [info script]] bug28388_extKO.brep] input
explode input
bop input_1 input_2
bopcommon result
set faces [explode result f]
set area [::single20::mass sprops result]
set validity [checkshape result]
::single20::assert nonempty_face [expr {[llength $faces]>0 && $area>1e-7}] "faces=[llength $faces] area=$area screen_only=1" numeric
::single20::assert validity [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"

puts "INPUT_DIAGNOSTIC input_1 [whatis input_1]"
puts [checkshape input_1]
puts [nbshapes input_1]
catch {puts "BOUNDS input_1 [::single20::bounds input_1]"}
catch {puts [sprops input_1 -full]}
catch {puts [vprops input_1 -full]}
puts "INPUT_DIAGNOSTIC input_2 [whatis input_2]"
puts [checkshape input_2]
puts [nbshapes input_2]
catch {puts "BOUNDS input_2 [::single20::bounds input_2]"}
catch {puts [sprops input_2 -full]}
catch {puts [vprops input_2 -full]}
puts "INPUT_DIAGNOSTIC result [whatis result]"
puts [checkshape result]
puts [nbshapes result]
catch {puts "BOUNDS result [::single20::bounds result]"}
catch {puts [sprops result -full]}
catch {puts [vprops result -full]}
::single20::finish
