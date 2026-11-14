set here [file dirname [info script]]
source [file join $here .. .. .. single20 assertions.tcl]
set model [file join $here .. .. .. .. .. issues occt-32929 1 public inputs bug32929.brep]
pload MODELING
restore $model b
ttranslate b 17 -13 9
explode b E
if {[llength [info commands blend]] != 1} {error "required blend command unavailable"}
if {![string match {*seems to be valid*} [checkshape b]]} {error "benchmark input invalid"}
::single20::assert input_valid 1 source_topology
puts START_BLEND
if {[catch {blend result b 1 b_8} operation_error]} {
    puts "BLEND_FAILED: $operation_error"
    ::single20::assert valid_result 0 operation_failed
    ::single20::assert face_count 0 operation_failed numeric
    ::single20::assert solid_count 0 operation_failed numeric
    ::single20::assert surface_area 0 operation_failed numeric
} else {
set valid [checkshape result]
set counts [nbshapes result]
set areaReport [sprops result 1e-5]
set areaOK 0
if {[regexp {Mass\s*:\s*([-+0-9.eE]+)} $areaReport match area]} {
    set areaOK [expr {abs($area - 13435.4) < 0.2}]
}
::single20::assert valid_result [string match {*seems to be valid*} $valid] topology
::single20::assert face_count [regexp -line {^\s*FACE\s*:\s*17\s*$} $counts] topology numeric
::single20::assert solid_count [regexp -line {^\s*SOLID\s*:\s*1\s*$} $counts] topology numeric
::single20::assert surface_area $areaOK geometry numeric
}
::single20::finish
