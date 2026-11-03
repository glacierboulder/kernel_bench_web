source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
set here [file dirname [info script]]
set healthy [expr {$::single20_case eq "healthy"}]
if {$healthy} {
    box first 10 10 10
    copy first second
    set expected 1000.0
    set expected_count 1
} else {
restore [file join $here bug28274-exact.brep] first
if {[llength [info commands bnondestructive]]} {bnondestructive 1}
copy first second
    set expected 741.787
    set expected_count 3
}
if {$::single20_case eq "rigid"} {
    trotate first second 0 0 0 0 0 1 30
    ttranslate first second 17 -29 43
}
set valid_inputs 1
foreach input_shape {first second} {
    set validity [checkshape $input_shape]
    puts "INPUT_VALIDITY $input_shape $validity"
    if {[string first "This shape seems to be valid" $validity] < 0} {set valid_inputs 0}
}
::single20::assert input_validity $valid_inputs "both_inputs_valid=$valid_inputs"
set first_box [::single20::bounds first]
set second_box [::single20::bounds second]
if {$healthy} {set operation_error [catch {eval mkvolume result [explode first f]} operation_log]} else {
set operation_error [catch {
set faces [explode first f]
if {$::single20_case eq "swap"} {set faces [lreverse $faces]}
eval mkvolume result $faces
} operation_log]
}
if {[info exists ::single20_negative]} {
    switch $::single20_negative {
        empty {compound result}
        shifted {ttranslate result 1000000 1000000 1000000}
        missing {
            set pieces [explode result so]
            set retained [lrange $pieces 0 end-1]
            eval compound $retained result
        }
    }
}
::single20::assert operation_completed [expr {$operation_error == 0}] "error=$operation_error report=$operation_log"
set valid 0
set validity unavailable
catch {set validity [checkshape result]; set valid [expr {[string first "This shape seems to be valid" $validity]>=0}]}
::single20::assert validity $valid "checkshape=$validity"
set pieces {}
compound result counted_result
catch {set pieces [explode counted_result so]}
::single20::assert component_count [expr {[llength $pieces]==$expected_count}] "observed=[llength $pieces] expected=$expected_count" numeric
set measured unknown
set measure_ok 0
set limit 1e-7
if {$expected ne "positive" && !$healthy} {set limit [expr {abs($expected)*1e-4}]}
if {![catch {set measured [::single20::mass vprops result]}]} {
    if {$expected eq "positive"} {set measure_ok [expr {$measured>1e-7}]} else {set measure_ok [expr {abs($measured-$expected)<=$limit}]}
}
::single20::assert measure $measure_ok "observed=$measured expected=$expected limit=$limit" numeric
set domain_ok 1
set center unavailable
if {[catch {vprops result center_x center_y center_z -full; set center [list [dval center_x] [dval center_y] [dval center_z]]}]} {
    set domain_ok 0
} else {
    for {set axis 0} {$axis<3} {incr axis} {
        set value [lindex $center $axis]
        set lower [expr {max([lindex $first_box $axis],[lindex $second_box $axis])}]
        set upper [expr {min([lindex $first_box [expr {$axis+3}]],[lindex $second_box [expr {$axis+3}]])}]
        if {![::single20::finite $value] || $value<$lower-1e-5 || $value>$upper+1e-5} {set domain_ok 0}
    }
}
::single20::assert centroid_domain $domain_ok "center=$center input1=$first_box input2=$second_box" numeric
set expected_area [expr {$healthy ? 600.0 : 985.692}]
set area [::single20::mass sprops result]
::single20::assert area [expr {abs($area-$expected_area)<=1e-4*$expected_area}] "area=$area expected=$expected_area relative_limit=1e-4" numeric
::single20::finish
