source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
set here [file dirname [info script]]
set healthy [expr {$::single20_case eq "healthy"}]
if {$healthy} {
box first 10 10 10
box second 5 0 0 10 10 10
} else {
restore [file join $here bug28195_solidsKO.brep] input
explode input
copy input_1 first
copy input_2 second
}
if {$::single20_case eq "rigid"} {
    trotate first second 0 0 0 0 0 1 30
    ttranslate first second 17 -29 43
}
set valid_inputs 1
foreach shape {first second} {
    set check [checkshape $shape]
    puts "INPUT_VALIDITY $shape $check"
    if {[string first "This shape seems to be valid" $check]<0} {set valid_inputs 0}
}
::single20::assert input_validity $valid_inputs "both_inputs_valid=$valid_inputs"
if {$::single20_case eq "swap"} {
    set operation_error [catch {bop second first; bopcommon result} operation_log]
} else {
    set operation_error [catch {bop first second; bopcommon result} operation_log]
}
if {[info exists ::single20_negative]} {
    switch $::single20_negative {
        empty {compound result}
        input_only {copy first result}
        shifted {ttranslate result 1000000 1000000 1000000}
    }
}
::single20::assert operation_completed [expr {$operation_error==0}] "error=$operation_error report=$operation_log"
set validity [checkshape result]
::single20::assert validity [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
set solids [explode result so]
::single20::assert topology [expr {[llength $solids]==1}] "solids=[llength $solids] expected=1" numeric
set upper [expr {min([::single20::mass vprops first],[::single20::mass vprops second])}]
set volume [::single20::mass vprops result]
::single20::assert volume_bounds [expr {$volume>1e-7 && $volume<=$upper+1e-4*$upper}] "volume=$volume max=$upper relative_limit=1e-4" numeric
set first_box [::single20::bounds first]
set second_box [::single20::bounds second]
set tested 0
set inside 0
set outside 0
set mismatches 0
foreach fx {0.13 0.31 0.5 0.69 0.87} {
    foreach fy {0.13 0.31 0.5 0.69 0.87} {
        foreach fz {0.13 0.31 0.5 0.69 0.87} {
            set coords {}
            set axis 0
            foreach fraction [list $fx $fy $fz] {
                set low [expr {min([lindex $first_box $axis],[lindex $second_box $axis])}]
                set high [expr {max([lindex $first_box [expr {$axis+3}]],[lindex $second_box [expr {$axis+3}]])}]
                lappend coords [expr {$low+$fraction*($high-$low)}]
                incr axis
            }
            eval point probe_point $coords
            set first_state UNKNOWN
            set second_state UNKNOWN
            regexp {The point is (IN|OUT|ON|UNKNOWN)} [bclassify first probe_point 1e-7] unused first_state
            regexp {The point is (IN|OUT|ON|UNKNOWN)} [bclassify second probe_point 1e-7] unused second_state
            if {$first_state eq "ON" || $second_state eq "ON"} {continue}
            if {$first_state eq "UNKNOWN" || $second_state eq "UNKNOWN"} {incr mismatches; continue}
            set expected [expr {$first_state eq "IN" && $second_state eq "IN" ? "IN" : "OUT"}]
            if {$expected eq "IN"} {incr inside} else {incr outside}
            incr tested
            set actual UNKNOWN
            if {[llength $solids]==1} {
                regexp {The point is (IN|OUT|ON|UNKNOWN)} [bclassify [lindex $solids 0] probe_point 1e-7] unused actual
            }
            if {$actual ne $expected} {incr mismatches; puts "MEMBERSHIP_MISMATCH point=$coords expected=$expected actual=$actual"}
        }
    }
}
::single20::assert volume_membership [expr {$tested>=100 && $inside>=2 && $outside>=2 && $mismatches==0}] "tested=$tested inside=$inside outside=$outside mismatches=$mismatches" numeric
::single20::finish
