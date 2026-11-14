set here [file dirname [info script]]
source [file join $here .. .. .. single20 assertions.tcl]
pload MODELING
box b 10 10 10
explode b E
blend result b 1 b_1
set areaReport [sprops result 1e-5]
set areaOK 0
if {[regexp {Mass\s*:\s*([-+0-9.eE]+)} $areaReport match area]} {
    set areaOK [expr {abs($area - (600 - 22 * (1 - acos(-1)/4))) < 0.02}]
}
::single20::assert normal_valid [string match {*seems to be valid*} [checkshape result]] topology
::single20::assert normal_area $areaOK analytic_area numeric
::single20::finish
