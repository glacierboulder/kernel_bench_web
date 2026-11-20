set ::axial_directory [file dirname [info script]]
source [file join $::axial_directory .. .. assertions.tcl]
source [file join $::axial_directory .. .. solid_checks.tcl]
pload TOPTEST

proc axial_inputs {dz rotation} {
    foreach {s file} {first cylinder second cone} {
        uplevel #0 [list restore [file join $::axial_directory .. 1 bug25542_${file}.brep] $s]
    }
    uplevel #0 [list ttranslate second 0 0 $dz]
    uplevel #0 [list trotate first second {*}$rotation]
}
proc axial_classify {shape} {
    set state UNKNOWN
    regexp {The point is (IN|ON|OUT|UNKNOWN)} [uplevel #0 [list bclassify $shape probe 1e-7]] -> state
    return $state
}
proc axial_mass {cmd eps} {
    set measured [uplevel #0 [list $cmd result $eps -full]]
    if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} $measured -> value] || ![::single20::finite $value]} {
        error "missing finite $cmd result at $eps"
    }
    return $value
}
proc axial_geometry {pose volume area count inside} {
    set conclusive_failure 0
    set ambiguous {}
    foreach input {first second} {
        set msg [uplevel #0 [list checkshape $input]]
        set stats [uplevel #0 [list nbshapes $input]]
        if {![regexp {SOLID\s*:\s*([0-9]+)} $stats -> ns] || $ns!=1} {error "operand must contain one solid"}
        set holder [uplevel #0 [list explode $input so]]
        if {![llength $holder]} {set holder [list $input]}
        if {[llength $holder]!=1} {error "operand traversal disagrees with solid count"}
        set input_solid($input) [lindex $holder 0]
        ::single20::assert ${input}_valid [expr {[string first "This shape seems to be valid" $msg]>=0}] $msg
    }
    set msg [uplevel #0 {checkshape result}]
    ::single20::assert validity [expr {[string first "This shape seems to be valid" $msg]>=0}] $msg
    set counts [uplevel #0 {nbshapes result}]
    if {![regexp {SOLID\s*:\s*([0-9]+)} $counts -> n]} {error "solid count missing"}
    set solids [uplevel #0 {explode result so}]
    if {$n==1 && ![llength $solids]} {set solids [list result]}
    if {[llength $solids]!=$n} {error "inconsistent solid traversal"}
    set closed 0
    if {$n==1} {
        set check [uplevel #0 {checkdiff first second result 1 1}]
        set closed [expr {[string first "Difference is Valid." $check]>=0}]
    }
    if {$n!=1 || !$closed} {set conclusive_failure 1}
    ::single20::assert topology [expr {$n==1 && $closed}] "solids=$n valid_closed_solid=$closed" numeric
    set measured [::single20::mass sprops result]
    if {abs($measured-$area)>abs($area)*1e-4} {set conclusive_failure 1}
    ::single20::assert draw_area [expr {abs($measured-$area)<=abs($area)*1e-4}] "observed=$measured expected=$area" numeric

    set box1 [::single20::bounds first]; set box2 [::single20::bounds second]
    uplevel #0 {sprops result cx cy cz -full}
    set center [uplevel #0 {list [dval cx] [dval cy] [dval cz]}]
    set ok 1
    for {set i 0} {$i<3} {incr i} {
        set v [lindex $center $i]; set j [expr {$i+3}]
        if {![::single20::finite $v] || $v<max([lindex $box1 $i],[lindex $box2 $i])-1e-5 ||
            $v>min([lindex $box1 $j],[lindex $box2 $j])+1e-5} {set ok 0}
    }
    if {!$ok} {set conclusive_failure 1}
    ::single20::assert centroid_domain $ok "centroid=$center" numeric
    foreach {name cmd target tol} [list volume vprops $volume 0.03 area sprops $area 0.02] {
        set coarse [axial_mass $cmd 1e-7]
        set fine [axial_mass $cmd 1e-10]
        set delta [expr {abs($fine-$target)}]; set drift [expr {abs($fine-$coarse)}]
        if {$delta>$tol+2*$drift} {set conclusive_failure 1} elseif {$delta+2*$drift>$tol} {lappend ambiguous $name}
        ::single20::assert $name [expr {$delta+2*$drift<=$tol}] "observed=$fine expected=$target drift=$drift limit=$tol" numeric
    }
    set total 0; set nin 0; set operands 0; set incorrect 0; set uncertain 0
    set fd [open [file join $::axial_directory $pose.points] r]
    while {[gets $fd row]>=0} {
        lassign $row x y z a b
        if {[llength $row]!=5 || $a ni {IN OUT} || $b ni {IN OUT}} {error "invalid witness record"}
        uplevel #0 [list point probe $x $y $z]
        if {[axial_classify $input_solid(first)] ne $a || [axial_classify $input_solid(second)] ne $b} {incr operands}
        set expected [expr {$a eq "IN" && $b eq "IN" ? "IN" : "OUT"}]
        if {$expected eq "IN"} {incr nin}
        set answer OUT
        if {$n==1} {set answer [axial_classify [lindex $solids 0]]}
        if {$n>1} {set answer UNKNOWN}
        if {$answer ni {IN OUT}} {incr uncertain} elseif {$answer ne $expected} {incr incorrect}
        incr total
    }
    close $fd
    if {$total!=$count || $inside!=$nin} {error "witness table incomplete"}
    ::single20::assert operand_membership [expr {$operands==0}] "tested=$total mismatched=$operands" numeric
    if {$incorrect} {set conclusive_failure 1}
    if {$uncertain} {lappend ambiguous result_membership}
    if {[llength $ambiguous] && !$conclusive_failure} {error "indeterminate geometry: $ambiguous"}
    ::single20::assert result_membership [expr {!$incorrect && !$uncertain}] "tested=$total wrong=$incorrect uncertain=$uncertain" numeric
    ::single20::finish
}
proc axial_run {pose dz rotation volume area count inside} {
    axial_inputs $dz $rotation
    uplevel #0 {bop first second; bopcommon result}
    ::single20::assert operation_completed 1 "Common returned"
    axial_geometry $pose $volume $area $count $inside
}
