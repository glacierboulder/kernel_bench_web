source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
restore [file join [file dirname [info script]] bug26580-plate-2.brep] first
restore [file join [file dirname [info script]] bug26776_b2.brep] second
bsection result first second
set edges [explode result e]
set vertices [explode result v]
set length [::single20::mass lprops result]
set validity [checkshape result]
::single20::assert branch [expr {[llength $edges]==1 && [llength $vertices]==2}] "edges=[llength $edges] vertices=[llength $vertices] screen_only=1" numeric
::single20::assert length [expr {abs($length-27.3439)<=1e-4*27.3439}] "length=$length expected=27.3439 upstream_relative_epsilon=1e-4 screen_only=1" numeric
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
