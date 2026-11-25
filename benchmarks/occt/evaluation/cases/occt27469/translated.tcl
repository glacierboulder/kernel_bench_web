source [file join [file dirname [info script]] .. single20 assertions.tcl]
source [file join [file dirname [info script]] body.tcl]
set ok [check_case translated]
::single20::assert boolean_geometry $ok geometry numeric
::single20::finish
