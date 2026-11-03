source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
if {$::single20_case eq "healthy"} {
    psphere first 10
    plane plane_support 0 0 0 0 0 1
    mkface second plane_support -20 20 -20 20
    set expected_length [expr {20*acos(-1)}]
    set length_limit 1e-6
} else {
    restore [file join [file dirname [info script]] bug23998_m1s.brep] input_compound
    explode input_compound
    copy input_compound_1 first
    copy input_compound_2 second
    set scale 1.0
    if {$::single20_case eq "rigid"} {
        trotate first second 0 0 0 0 0 1 30
        ttranslate first second 17 -29 43
    }
    if {$::single20_case eq "scale"} {
        set scale 2.0
        tscale first second 0 0 0 $scale
    }
    set expected_length [expr {67.026*$scale}]
    set length_limit [expr {0.0005*$scale}]
}
set allowed_bounds [::single20::bounds first]
set error_code [catch {bop first second; bopsection result} operation_log]
if {[info exists ::single20_negative]} {
    switch $::single20_negative {
        empty {compound result}
        duplicate {copy result saved_result; compound saved_result saved_result result}
        shifted {ttranslate result 10000 10000 10000}
    }
}
::single20::assert operation_completed [expr {$error_code == 0}] "error=$error_code report=$operation_log"
set valid 0
set description unavailable
if {![catch {checkshape result} description]} {
    set valid [expr {[string first "This shape seems to be valid" $description] >= 0}]
}
::single20::assert shape_valid $valid "checkshape=$description"
set edges {}
set vertices {}
catch {set edges [explode result e]; set vertices [explode result v]}
::single20::assert closed_single_edge [expr {[llength $edges] == 1 && [llength $vertices] == 1}] "edges=[llength $edges] vertices=[llength $vertices]" numeric
set length unknown
set length_ok 0
if {![catch {set length [::single20::mass lprops result]}]} {
    set length_ok [expr {abs($length-$expected_length) <= $length_limit}]
}
::single20::assert section_length $length_ok "observed=$length expected=$expected_length limit=$length_limit" numeric
set bounds_ok 1
set measured unavailable
if {[catch {
    lprops result center_x center_y center_z -full
    set measured [list [dval center_x] [dval center_y] [dval center_z]]
}]} {
    set bounds_ok 0
} else {
    for {set i 0} {$i < 3} {incr i} {
        set coordinate [lindex $measured $i]
        if {![::single20::finite $coordinate] || $coordinate < [lindex $allowed_bounds $i]-1e-5 ||
            $coordinate > [lindex $allowed_bounds [expr {$i+3}]]+1e-5} {
            set bounds_ok 0
        }
    }
}
::single20::assert centroid_domain $bounds_ok "centroid=$measured containing_input_box=$allowed_bounds" numeric
::single20::finish
