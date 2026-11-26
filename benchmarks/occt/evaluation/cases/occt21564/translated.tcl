set here [file dirname [info script]]
source [file join $here .. single20 assertions.tcl]
source [file join $here geometry.tcl]
set ok [section_trial translated]
::single20::assert boolean_geometry $ok section numeric
::single20::finish
