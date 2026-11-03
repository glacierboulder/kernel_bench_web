source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
if {$::single20_case eq "healthy"} {
    box first 10 10 10
    box second 5 0 0 10 10 10
    set expectations {{common 400.0 1e-7 500.0 1e-7} {cut 400.0 1e-7 500.0 1e-7}}
} else {
    restore [file join [file dirname [info script]] bug31850.brep] source_compound
    explode source_compound
    copy source_compound_1 first
    copy source_compound_2 second
    if {$::single20_case eq "rigid"} {
        trotate first second 0 0 0 0 0 1 90
        ttranslate first second 17 -29 43
    }
    if {$::single20_case eq "fuzzy"} {
        bfuzzyvalue 1e-6
        bnondestructive 1
    }
    # Half a unit in each printed upstream property's last decimal place.
    set expectations {{common 1107.94 0.005 472.151 0.0005} {cut 5244.61 0.005 2516.56 0.005}}
}
set allowed_bounds [::single20::bounds first]
foreach expectation $expectations {
    lassign $expectation operation area area_limit volume volume_limit
    set error_code [catch {b$operation result first second} operation_log]
    if {[info exists ::single20_negative]} {
        switch $::single20_negative {
            empty {compound result}
            input_only {copy first result}
            shifted {ttranslate result 10000 10000 10000}
        }
    }
    ::single20::assert ${operation}_completed [expr {$error_code == 0}] "error=$error_code report=$operation_log"
    ::single20::solid_result $operation result $area $area_limit $volume $volume_limit $allowed_bounds
}
::single20::finish
