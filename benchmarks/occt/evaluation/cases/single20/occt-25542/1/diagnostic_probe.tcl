source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
restore [file join [file dirname [info script]] bug25542_cylinder.brep] first
restore [file join [file dirname [info script]] bug25542_cone.brep] second
bop first second
bopcommon result
set solids [explode result so]
set faces [explode result f]
set area [::single20::mass sprops result]
set validity [checkshape result]
::single20::assert topology [expr {[llength $solids]==1 && [llength $faces]==3}] "solids=[llength $solids] faces=[llength $faces] screen_only=1" numeric
::single20::assert area [expr {abs($area-6951.3)<=1e-4*6951.3}] "area=$area expected=6951.3 upstream_relative_epsilon=1e-4 screen_only=1" numeric
::single20::assert validity [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"

puts "INPUT_DIAGNOSTIC first [whatis first]"
puts [checkshape first]
puts [nbshapes first]
catch {puts "BOUNDS first [::single20::bounds first]"}
catch {puts [sprops first -full]}
catch {puts [vprops first -full]}
puts "INPUT_DIAGNOSTIC second [whatis second]"
puts [checkshape second]
puts [nbshapes second]
catch {puts "BOUNDS second [::single20::bounds second]"}
catch {puts [sprops second -full]}
catch {puts [vprops second -full]}
puts "INPUT_DIAGNOSTIC result [whatis result]"
puts [checkshape result]
puts [nbshapes result]
catch {puts "BOUNDS result [::single20::bounds result]"}
catch {puts [sprops result -full]}
catch {puts [vprops result -full]}
::single20::finish
