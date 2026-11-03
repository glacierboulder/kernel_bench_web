source [file join [file dirname [info script]] .. .. assertions.tcl]
pload TOPTEST
lassign $::single20_case scale translated healthy
if {$healthy} {
    sphere first_support 0 0 0 10
    plane second_support 0 0 0 0 0 1
    mkface first first_support
    mkface second second_support -20 20 -20 20
    set expected_count 1
} else {
    restore [file join [file dirname [info script]] bug25890_f1.brep] first
    restore [file join [file dirname [info script]] bug25890_f2.brep] second
    if {$scale != 1} {tscale first second 0 0 0 $scale}
    if {$translated} {ttranslate first second 17 -29 43}
    mksurface first_support first
    mksurface second_support second
    set expected_count 5
}
set operation_error [catch {bopcurves first second} operation_log]
mkface measure_first first_support
mkface measure_second second_support
set curves {}
for {set i 1} {$i <= 32} {incr i} {
    if {[catch {whatis c_$i} description] || [string first "3d curve" $description] < 0} {break}
    lappend curves c_$i
}
if {[info exists ::single20_negative]} {
    switch $::single20_negative {
        missing {set curves [lrange $curves 0 end-1]}
        duplicate {set curves [lreplace $curves 1 1 [lindex $curves 0]]}
        shifted {translate [lindex $curves 0] 1000 0 0}
    }
}
::single20::assert operation_completed [expr {$operation_error == 0}] "error=$operation_error report=$operation_log"
::single20::assert branch_count [expr {[llength $curves] == $expected_count}] "observed=[llength $curves] expected=$expected_count" numeric
set support_ok [expr {[llength $curves] == $expected_count}]
set max_distance 0.0
set measurement_count 0
set curve_index 0
set edges {}
foreach curve $curves {
    if {[catch {bounds $curve low high; set lower [dval low]; set upper [dval high]}] ||
        ![::single20::finite $lower] || ![::single20::finite $upper] || $upper <= $lower} {
        set support_ok 0
        continue
    }
    for {set sample 0} {$sample <= 16} {incr sample} {
        set parameter [expr {$lower+($upper-$lower)*$sample/16.0}]
        if {[catch {cvalue $curve $parameter px py pz; set x [dval px]; set y [dval py]; set z [dval pz]}] ||
            ![::single20::finite $x] || ![::single20::finite $y] || ![::single20::finite $z]} {
            set support_ok 0
            continue
        }
        vertex sample_point $x $y $z
        foreach support {measure_first measure_second} {
            incr measurement_count
            catch {unset measured_distance_val}
            if {[catch {distmini measured_distance sample_point $support}] ||
                ![info exists measured_distance_val] ||
                [catch {set distance [dval measured_distance_val]}] || ![::single20::finite $distance]} {
                set support_ok 0
            } else {
                set max_distance [expr {max($max_distance,$distance)}]
                if {$distance > 1e-5*$scale} {set support_ok 0}
            }
        }
    }
    set name measured_edge_$curve_index
    if {[catch {mkedge $name $curve}]} {set support_ok 0} else {lappend edges $name}
    incr curve_index
}
::single20::assert support_distances $support_ok "max_distance=$max_distance limit=[expr {1e-5*$scale}] measurement_points=$measurement_count" numeric
set overlap_ok [expr {[llength $edges] == $expected_count}]
set pairs 0
set overlapping_edges 0
for {set i 0} {$i < [llength $edges]} {incr i} {
    for {set j [expr {$i+1}]} {$j < [llength $edges]} {incr j} {
        incr pairs
        catch {unset pair_common}
        set report unavailable
        if {[catch {bcommon pair_common [lindex $edges $i] [lindex $edges $j]} report] ||
            [regexp -nocase {error|warning|exception} $report]} {
            set overlap_ok 0
            continue
        }
        if {[catch {whatis pair_common} description] || [string first "shape" $description] < 0} {
            set overlap_ok 0
            continue
        }
        set shared [explode pair_common e]
        incr overlapping_edges [llength $shared]
        if {[llength $shared] > 0} {set overlap_ok 0}
    }
}
::single20::assert no_curve_overlap $overlap_ok "pairs=$pairs overlapping_edges=$overlapping_edges" numeric
::single20::finish
