set here [file dirname [info script]]
set assetdir [file join $here assets]
source [file join $here .. single20 assertions.tcl]
source [file join $here geometry.tcl]
::single20::assert boolean_geometry [section_trial original] geometry numeric
::single20::finish
