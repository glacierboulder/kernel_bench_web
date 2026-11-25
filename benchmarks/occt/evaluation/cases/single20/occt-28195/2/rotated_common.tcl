namespace eval ::m28195 {
    variable directory [file dirname [info script]]
}
source [file join $::m28195::directory .. .. assertions.tcl]
source [file join $::m28195::directory .. .. solid_checks.tcl]
pload TOPTEST

proc ::m28195::load_operands {rotation} {
    variable directory
    uplevel #0 [list restore [file join $directory .. 1 bug28195_solidsKO.brep] input]
    # Placement of the compound before decomposition is part of the reproducer.
    uplevel #0 [list trotate input {*}$rotation]
    uplevel #0 {explode input}
}

proc ::m28195::valid {shape} {
    set report [uplevel #0 [list checkshape $shape]]
    return [expr {[string first "This shape seems to be valid" $report] >= 0}]
}

proc ::m28195::solids {shape} {
    set counts [uplevel #0 [list nbshapes $shape]]
    if {![regexp -line {^\s*SOLID\s*:\s*([0-9]+)} $counts -> count]} {
        error "missing solid count for $shape"
    }
    set parts [uplevel #0 [list explode $shape so]]
    if {$count == 1 && ![llength $parts]} {return [list $shape]}
    if {[llength $parts] != $count} {error "solid traversal disagrees with nbshapes for $shape"}
    return $parts
}

proc ::m28195::close_volume {actual expected} {
    return [expr {[::single20::finite $actual] && abs($actual-$expected) <= 1e-4*abs($expected)}]
}

proc ::m28195::classify {shape} {
    set state UNKNOWN
    regexp {The point is (IN|OUT|ON|UNKNOWN)} [uplevel #0 [list bclassify $shape probe 1e-7]] -> state
    return $state
}

proc ::m28195::check_geometry {pose rigid_volume} {
    variable directory
    foreach {operand gold} {input_1 725572727.0119817 input_2 190578321.74481627} {
        set volume [::single20::mass vprops $operand]
        set count [llength [solids $operand]]
        ::single20::assert ${operand}_qualified [expr {[valid $operand] && $count == 1 && [close_volume $volume $gold]}] \
            "solids=$count volume=$volume expected=$gold" numeric
    }
    set valid_result [valid result]
    ::single20::assert validity $valid_result "result_valid=$valid_result"
    set parts [solids result]
    ::single20::assert topology [expr {[llength $parts] == 1}] "solids=[llength $parts] expected=1" numeric
    set volume [::single20::mass vprops result]
    ::single20::assert volume [expr {[close_volume $volume 172189705.92920932] && [close_volume $volume $rigid_volume]}] \
        "observed=$volume rigid_reference=$rigid_volume canonical=172189705.92920932 relative_limit=1e-4" numeric

    set bad_inputs {}
    set bad_grid {}
    set bad_target {}
    set seen [dict create]
    set inside 0
    set targets 0
    set fd [open [file join $directory $pose.points] r]
    while {[gets $fd line] >= 0} {
        lassign $line id a b common x y z
        if {[llength $line] != 7 || [dict exists $seen $id] || $a ni {IN OUT} || $b ni {IN OUT} ||
            $common ne [expr {$a eq "IN" && $b eq "IN" ? "IN" : "OUT"}]} {error "invalid witness $id"}
        dict set seen $id 1
        set targeted [string match "target-*" $id]
        if {$targeted} {
            incr targets
            if {$a ne "OUT" || $b ne "IN"} {error "invalid exclusion witness $id"}
        }
        if {$common eq "IN"} {incr inside}
        uplevel #0 [list point probe $x $y $z]
        if {[classify input_1] ne $a || [classify input_2] ne $b} {lappend bad_inputs $id}
        set actual OUT
        foreach s $parts {
            set state [classify $s]
            if {$state eq "IN"} {set actual IN; break}
            if {$state ne "OUT"} {set actual $state}
        }
        if {$actual ne $common} {
            if {$targeted} {lappend bad_target $id} else {lappend bad_grid $id}
        }
    }
    close $fd
    if {[dict size $seen] != 129 || $inside != 17 || $targets != 4} {error "incomplete witness table"}
    ::single20::assert operand_membership [expr {![llength $bad_inputs]}] "tested=129 mismatches=$bad_inputs" numeric
    ::single20::assert grid_membership [expr {![llength $bad_grid]}] "tested=125 mismatches=$bad_grid" numeric
    ::single20::assert exclusion_membership [expr {![llength $bad_target]}] "tested=4 mismatches=$bad_target" numeric
    ::single20::finish
}

proc ::m28195::run {pose rotation rigid_volume} {
    load_operands $rotation
    uplevel #0 {bop input_1 input_2; bopcommon result}
    ::single20::assert operation_completed 1 "bop and bopcommon returned"
    check_geometry $pose $rigid_volume
}
