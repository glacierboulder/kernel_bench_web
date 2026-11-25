# Apply the original DRAW command to the same infinite analytic surfaces.
pload MODELING

proc freeze_intersection {root prefix} {
    set names {}
    if {[string first "3d curve" [uplevel #0 [list whatis $root]]] >= 0} {
        lappend names $root
    }
    for {set i 1} {$i <= 128} {incr i} {
        set name ${root}_$i
        if {[string first "3d curve" [uplevel #0 [list whatis $name]]] < 0} {
            break
        }
        lappend names $name
    }
    if {$i > 128} {error "intersection enumeration exceeded limit"}
    set paths {}
    foreach name $names {
        set path [file join [pwd] "${prefix}-${name}.draw"]
        uplevel #0 [list save $name $path]
        if {![file isfile $path]} {error "DRAW serialization missing"}
        lappend paths $path
    }
    return $paths
}

proc judge {python checker label role paths expected} {
    set code [catch {exec $python -B $checker $role {*}$paths 2>@1} output details]
    if {$output ne ""} {puts $output}
    set status 0
    if {$code} {
        set e [dict get $details -errorcode]
        if {[lindex $e 0] ne "CHILDSTATUS"} {error $output}
        set status [lindex $e 2]
    }
    if {$status != $expected} {
        if {$status == 2} {error "coverage could not be certified for $label"}
        puts stderr "BENCH_ASSERT_FAIL kind=expression label=$label detail=exit_$status"
        puts stderr "BENCH_ORACLE_FAILED assertions=1 failures=1"
        error "one or more benchmark assertions failed"
    }
    puts "BENCH_ASSERT_PASS kind=expression label=$label detail=exit_$status"
}

set here [file dirname [file normalize [info script]]]
set python [file join $env(CONDA_PREFIX) bin python]
set checker [file join $here coverage.py]
cylinder far1 -106.471129473161 -64.3442185874231 -19.25 1 0 0 0 0 -1 0.25
cylinder far2 900 600 400 0 0 1 1 0 0 3
intersect far_result far1 far2 1.0e-4
judge $python $checker native-empty far [freeze_intersection far_result live-far] 0

cylinder s1 -106.471129473161 -64.3442185874231 -19.25 1 0 0 0 0 -1 0.25
cylinder s2 -124.971129473161 -67.0942185874231 -20.5 0 0 1 1 0 0 3
intersect regular s1 s2 1.0e-4
judge $python $checker native-full regular [freeze_intersection regular live-regular] 0

foreach role {healthy-1 healthy-2 duplicate} {
    set inputs {}
    for {set i 1} {$i <= 4} {incr i} {
        lappend inputs [file join $here "$role-regular-$i.draw"]
    }
    judge $python $checker $role regular $inputs [expr {$role eq "duplicate"}]
}
judge $python $checker false-far false-far [list [file join $here false-far-far-1.draw]] 1
puts "BENCH_ORACLE_OK assertions=6 numeric_assertions=0"
puts "TEST_DONE assertions=6 numeric_assertions=0"
