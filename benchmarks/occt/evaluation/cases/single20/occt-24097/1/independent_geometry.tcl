source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
set here [file dirname [info script]]
set healthy [expr {$::single20_case eq "healthy"}]
if {$healthy} {
    plane first_support 0 0 0 0 0 1
    plane second_support 0 0 0 0 1 0
    mkface first first_support -5 5 -5 5
    mkface second second_support -5 5 -5 5
    set expected 10.0
    set expected_count 1
} else {
restore [file join $here bug24097_face1.brep] first
restore [file join $here bug24097_face2.brep] second
    set expected 0.12505590740085806
    set expected_count 1
}
if {$::single20_case eq "rigid"} {
    trotate first second 0 0 0 0 0 1 30
    ttranslate first second 17 -29 43
}
if {$::single20_case eq "swap"} {
    renamevar first held_first
    renamevar second first
    renamevar held_first second
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
if {$healthy} {set operation_error [catch {bsection result first second} operation_log]} else {
set operation_error [catch {
bsection result first second
} operation_log]
}
if {[info exists ::single20_negative]} {
    switch $::single20_negative {
        empty {compound result}
        shifted {ttranslate result 1000000 1000000 1000000}
        missing {
            set pieces [explode result e]
            if {[llength $pieces] == 1} {
                mkcurve piece_curve [lindex $pieces 0]
                bounds piece_curve low high
                mkedge shortened piece_curve [dval low] [expr {([dval low]+[dval high])/2.0}]
                compound shortened result
            } else {
                set retained [lrange $pieces 0 end-1]
                eval compound $retained result
            }
        }
    }
}
::single20::assert operation_completed [expr {$operation_error == 0}] "error=$operation_error report=$operation_log"
set valid 0
set validity unavailable
catch {set validity [checkshape result]; set valid [expr {[string first "This shape seems to be valid" $validity]>=0}]}
::single20::assert validity $valid "checkshape=$validity"
set pieces {}
catch {set pieces [explode result e]}
::single20::assert component_count [expr {[llength $pieces]==$expected_count}] "observed=[llength $pieces] expected=$expected_count" numeric
set measured unknown
set measure_ok 0
set limit 1e-7
if {!$healthy} {set limit 1e-6}
if {![catch {set measured [::single20::mass lprops result]}]} {
    if {$expected eq "positive"} {set measure_ok [expr {$measured>1e-7}]} else {set measure_ok [expr {abs($measured-$expected)<=$limit}]}
}
::single20::assert measure $measure_ok "observed=$measured expected=$expected limit=$limit" numeric
set domain_ok 1
set center unavailable
if {[catch {lprops result center_x center_y center_z -full; set center [list [dval center_x] [dval center_y] [dval center_z]]}]} {
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
set vertices [explode result v]
::single20::assert endpoints [expr {[llength $vertices]==2}] "vertices=[llength $vertices] expected=2" numeric
set witnesses {{227.64587032755415 17.256486415194125 19.190000000000012} {227.6607085833758 17.251425563295694 19.190357782657983} {227.67553185003874 17.246364711397028 19.19071556531598} {227.69034012239229 17.24130385949814 19.191073347973973} {227.7051333955729 17.236243007598997 19.191431130632} {227.71991166500356 17.231182155699614 19.191788913290047} {227.73467492639344 17.226121303800007 19.192146695948114} {227.74942317573698 17.22106045190012 19.192504478606185} {227.7641564093142 17.215999600000004 19.192862261264267}}
if {$healthy} {set witnesses {{-5 0 0} {0 0 0} {5 0 0}}}
set witness_ok 1
set maximum 0.0
foreach point $witnesses {
    lassign $point x y z
    if {$::single20_case eq "rigid"} {
        set angle [expr {acos(-1)/6}]
        set tx [expr {cos($angle)*$x-sin($angle)*$y+17}]
        set ty [expr {sin($angle)*$x+cos($angle)*$y-29}]
        set x $tx
        set y $ty
        set z [expr {$z+43}]
    }
    vertex reference_point $x $y $z
    if {[catch {distmini independent_distance reference_point result; set distance [dval independent_distance_val]}] || ![::single20::finite $distance]} {
        set witness_ok 0
    } else {
        set maximum [expr {max($maximum,$distance)}]
        if {$distance>1e-6} {set witness_ok 0}
    }
}
::single20::assert independent_curve_coverage $witness_ok "witnesses=[llength $witnesses] maximum=$maximum absolute_limit=1e-6" numeric
::single20::finish
