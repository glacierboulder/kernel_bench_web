source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
if {$::single20_case eq "healthy"} {
    box first 10 10 10
    box second 5 0 0 10 10 10
    set expected_area 400.0
    set area_limit 1e-7
    set expected_volume 500.0
    set volume_limit 1e-7
} else {
    restore [file join [file dirname [info script]] bug26243_anc101.brep] first
    tcopy first second
    trotate second 155 100.75 0 0 0 1 90
    if {$::single20_case eq "rigid"} {
        trotate first second 0 0 0 0 0 1 30
        ttranslate first second 17 -29 43
    }
    if {$::single20_case eq "swap"} {
        renamevar first saved_first
        renamevar second first
        renamevar saved_first second
    }
    # The upstream area is rounded to the nearest unit.
    set expected_area 272911.0
    set area_limit 0.5
    set expected_volume positive
    set volume_limit unused
}
set allowed_bounds [::single20::bounds first]
set error_code [catch {bcommon result first second} operation_log]
if {[info exists ::single20_negative]} {
    switch $::single20_negative {
        empty {compound result}
        input_only {copy first result}
        shifted {ttranslate result 10000 10000 10000}
    }
}
::single20::assert operation_completed [expr {$error_code == 0}] "error=$error_code report=$operation_log"
::single20::solid_result common result $expected_area $area_limit $expected_volume $volume_limit $allowed_bounds
::single20::finish
