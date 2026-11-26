set here [file dirname [info script]]
source [file join $here .. single20 assertions.tcl]
source [file join $here geometry.tcl]
set ok [measure_trial translated [file join $here assets]]
::single20::assert boolean_geometry $ok fuse numeric
::single20::finish
