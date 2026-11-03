source [file join [file dirname [info script]] .. .. assertions.tcl]
pload TOPTEST
lassign $::single20_case tool_file dz expected_volume rigid
restore [file join [file dirname [info script]] inputs cylinder.brep] cylinder_shape
restore [file join [file dirname [info script]] inputs $tool_file] tool_shape
foreach shape {cylinder_shape tool_shape} {
    set validity [checkshape $shape]
    if {[string first "This shape seems to be valid" $validity] < 0} {
        error "input validity failed for $shape"
    }
}
if {$rigid} {
    trotate cylinder_shape tool_shape 0 0 0 0 0 1 90
    ttranslate cylinder_shape tool_shape 17 -29 43
}
set error_code [catch {bcut result cylinder_shape tool_shape} operation_log]
if {[info exists ::single20_negative]} {
    switch $::single20_negative {
        unchanged {copy cylinder_shape result}
        empty {compound result}
        shifted {ttranslate result 10000 10000 10000}
    }
}
::single20::assert operation_completed [expr {$error_code == 0}] "error=$error_code report=$operation_log"
set validity unavailable
set valid 0
if {![catch {checkshape result} validity]} {
    set valid [expr {[string first "This shape seems to be valid" $validity] >= 0}]
}
::single20::assert shape_valid $valid "checkshape=$validity"
set solids {}
catch {set solids [explode result so]}
::single20::assert solid_count [expr {[llength $solids] == 1}] "observed=[llength $solids] expected=1" numeric
set volume unknown
set volume_ok 0
if {![catch {vprops result 1e-10 -full} properties] &&
    [regexp {Mass\s*:\s*([-+0-9.eE]+)} $properties unused volume] && [::single20::finite $volume]} {
    set volume_ok [expr {abs($volume-$expected_volume) <= 0.1}]
}
::single20::assert analytic_volume $volume_ok "observed=$volume ideal_tube=$expected_volume absolute_limit=0.1 adaptive_integration_epsilon=1e-10" numeric
foreach id {kept_core removed_middle removed_top} z {15.0 22.0 29.7} expected_state {IN OUT OUT} {
    set x 0.0
    set y 0.0
    if {$expected_state eq "OUT"} {
        set theta [expr {($z-$dz)*acos(-1)}]
        set x [expr {7.7*cos($theta)}]
        set y [expr {7.7*sin($theta)}]
    }
    if {$rigid} {
        set saved_x $x
        set x [expr {17-$y}]
        set y [expr {$saved_x-29}]
        set z [expr {$z+43}]
    }
    point witness $x $y $z
    set classification unavailable
    set point_ok 0
    if {[llength $solids] == 1 && ![catch {bclassify [lindex $solids 0] witness 1e-7} classification]} {
        set point_ok [regexp "\\m${expected_state}\\M" $classification]
    }
    ::single20::assert $id $point_ok "point=($x,$y,$z) expected=$expected_state observed=$classification"
}
::single20::finish
