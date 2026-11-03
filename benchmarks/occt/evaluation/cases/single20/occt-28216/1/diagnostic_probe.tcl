source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
restore [file join [file dirname [info script]] bug28216_initSurf.brep] face
restore [file join [file dirname [info script]] bug28216_solid.brep] solid
bop face solid
bopcommon result
set faces [explode result f]
set edges [explode result e]
set vertices [explode result v]
set area [::single20::mass sprops result]
set validity [checkshape result]
::single20::assert topology [expr {[llength $faces]==1 && [llength $edges]==4 && [llength $vertices]==4}] "faces=[llength $faces] edges=[llength $edges] vertices=[llength $vertices] screen_only=1" numeric
::single20::assert nonzero_area [expr {$area>1e-7}] "area=$area screen_only=1" numeric
::single20::assert validity [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"

puts "INPUT_DIAGNOSTIC face [whatis face]"
puts [checkshape face]
puts [nbshapes face]
catch {puts "BOUNDS face [::single20::bounds face]"}
catch {puts [sprops face -full]}
catch {puts [vprops face -full]}
puts "INPUT_DIAGNOSTIC solid [whatis solid]"
puts [checkshape solid]
puts [nbshapes solid]
catch {puts "BOUNDS solid [::single20::bounds solid]"}
catch {puts [sprops solid -full]}
catch {puts [vprops solid -full]}
puts "INPUT_DIAGNOSTIC result [whatis result]"
puts [checkshape result]
puts [nbshapes result]
catch {puts "BOUNDS result [::single20::bounds result]"}
catch {puts [sprops result -full]}
catch {puts [vprops result -full]}
::single20::finish
