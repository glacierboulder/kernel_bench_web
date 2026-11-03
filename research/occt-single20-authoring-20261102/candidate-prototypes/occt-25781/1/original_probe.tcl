source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
pcylinder first 5 50 360
ptorus second 20 5 -180 180 360
trotate second 0 0 0 1 0 0 90
ttranslate second 20 0 0
set first_volume [::single20::mass vprops first]
set second_volume [::single20::mass vprops second]
bfuse result first second
set volume [::single20::mass vprops result]
set validity [checkshape result]
set solids [explode result so]
::single20::assert valid_result [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
::single20::assert connected_union [expr {[llength $solids]==1 && $volume>max($first_volume,$second_volume) && $volume<$first_volume+$second_volume}] "solids=[llength $solids] volume=$volume input_a=$first_volume input_b=$second_volume" numeric
::single20::finish
