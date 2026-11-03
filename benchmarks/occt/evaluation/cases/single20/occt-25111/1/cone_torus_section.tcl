source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
lassign $::single20_case scale translated healthy
set ox [expr {$translated ? 17.0 : 0.0}]
set oy [expr {$translated ? -29.0 : 0.0}]
set oz [expr {$translated ? 43.0 : 0.0}]
restore [file join [file dirname [info script]] bug25111_s1.draw] first_support
mkface first first_support
if {$healthy} {
    plane second_support 0 0 2 0 0 1
    mkface second second_support -20 20 -20 20
    set expected_length [expr {28*acos(-1)*$scale}]
    set length_limit [expr {1e-5*$scale}]
} else {
    restore [file join [file dirname [info script]] bug25111_s2.draw] second_support
    mkface second second_support
    set expected_length [expr {53.1714*$scale}]
    set length_limit [expr {1e-4*$expected_length}]
}
if {$scale != 1} {tscale first second 0 0 0 $scale}
if {$translated} {ttranslate first second $ox $oy $oz}
set operation_error [catch {bop first second; bopsection result} operation_log]
set edges {}
catch {set edges [explode result e]}
if {[info exists ::single20_negative]} {
    switch $::single20_negative {
        missing {set edges [lrange $edges 0 end-1]; eval compound $edges result}
        empty {compound result; set edges {}}
        shifted {ttranslate result 1000 0 0; set edges [explode result e]}
    }
}
::single20::assert operation_completed [expr {$operation_error == 0}] "error=$operation_error report=$operation_log"
set valid 0
set validity unavailable
if {![catch {checkshape result} validity]} {
    set valid [expr {[string first "This shape seems to be valid" $validity] >= 0}]
}
::single20::assert shape_valid $valid "checkshape=$validity"
set length unknown
set length_ok 0
if {![catch {set length [::single20::mass lprops result]}]} {
    set length_ok [expr {abs($length-$expected_length) <= $length_limit}]
}
::single20::assert section_length $length_ok "observed=$length expected=$expected_length limit=$length_limit" numeric
set support_ok [expr {[llength $edges] > 0}]
set graph_ok $support_ok
set maximum 0.0
set nodes {}
array set degree {}
array set neighbors {}
set index 0
foreach edge $edges {
    set curve curve_$index
    incr index
    if {[catch {mkcurve $curve $edge; bounds $curve low high; set lower [dval low]; set upper [dval high]}] ||
        ![::single20::finite $lower] || ![::single20::finite $upper] || $upper <= $lower} {
        set support_ok 0
        set graph_ok 0
        continue
    }
    set pair {}
    for {set i 0} {$i <= 32} {incr i} {
        set parameter [expr {$lower+($upper-$lower)*$i/32.0}]
        if {[catch {cvalue $curve $parameter px py pz; set x [dval px]; set y [dval py]; set z [dval pz]}] ||
            ![::single20::finite $x] || ![::single20::finite $y] || ![::single20::finite $z]} {
            set support_ok 0
            set graph_ok 0
            continue
        }
        set x [expr {($x-$ox)/$scale}]
        set y [expr {($y-$oy)/$scale}]
        set z [expr {($z-$oz)/$scale}]
        set cone_error [expr {abs(sqrt($x*$x+$y*$y)-(15-0.5*$z))/sqrt(1.25)}]
        if {$healthy} {
            set other_error [expr {abs($z-2)}]
        } else {
            set other_error [expr {abs(sqrt(pow(sqrt($x*$x+pow($y-10,2))-20,2)+$z*$z)-5)}]
        }
        set maximum [expr {max($maximum,$cone_error,$other_error)}]
        if {$cone_error > 1e-5 || $other_error > 1e-5 || $z < -1e-5 || $z > 10+1e-5} {set support_ok 0}
        if {$i == 0 || $i == 32} {
            set match -1
            for {set node 0} {$node < [llength $nodes]} {incr node} {
                lassign [lindex $nodes $node] nx ny nz
                if {sqrt(pow($x-$nx,2)+pow($y-$ny,2)+pow($z-$nz,2)) <= 1e-5} {set match $node; break}
            }
            if {$match < 0} {
                set match [llength $nodes]
                lappend nodes [list $x $y $z]
                set degree($match) 0
                set neighbors($match) {}
            }
            incr degree($match)
            lappend pair $match
        }
    }
    if {[llength $pair] != 2} {set graph_ok 0; continue}
    lassign $pair first_node second_node
    lappend neighbors($first_node) $second_node
    lappend neighbors($second_node) $first_node
}
::single20::assert analytic_support $support_ok "normalized_max_distance=$maximum limit=1e-5 scale=$scale" numeric
set visited {}
set open_ends 0
if {[llength $nodes]} {
    set pending {0}
    while {[llength $pending]} {
        set node [lindex $pending end]
        set pending [lrange $pending 0 end-1]
        if {[lsearch -exact $visited $node] >= 0} {continue}
        lappend visited $node
        if {$degree($node) == 1} {incr open_ends} elseif {$degree($node) != 2} {set graph_ok 0}
        foreach next $neighbors($node) {lappend pending $next}
    }
}
set expected_ends [expr {$healthy ? 0 : 2}]
if {[llength $visited] != [llength $nodes] || $open_ends != $expected_ends} {set graph_ok 0}
::single20::assert connected_component $graph_ok "nodes=[llength $nodes] connected=[llength $visited] open_ends=$open_ends expected_ends=$expected_ends" numeric
set witnesses {}
if {$healthy} {
    set witnesses {{14 0 2} {-14 0 2} {0 14 2} {0 -14 2}}
} else {
    foreach z {0.0 1.0 4.5 5.0} {
        set radius [expr {15-0.5*$z}]
        set radial_signs {-1 1}
        if {$z == 0.0 || $z == 5.0} {set radial_signs {-1}}
        foreach sign $radial_signs {
            set rho [expr {20+$sign*sqrt(25-$z*$z)}]
            if {$rho > $radius+10 || $rho < abs($radius-10)} {continue}
            set y [expr {($radius*$radius+100-$rho*$rho)/20.0}]
            set x [expr {sqrt(max(0.0,$radius*$radius-$y*$y))}]
            lappend witnesses [list $x $y $z] [list [expr {-$x}] $y $z]
        }
    }
}
set coverage_ok [expr {[llength $edges] > 0}]
set worst_witness 0.0
foreach witness $witnesses {
    lassign $witness x y z
    vertex analytic_point [expr {$ox+$scale*$x}] [expr {$oy+$scale*$y}] [expr {$oz+$scale*$z}]
    if {[catch {distmini probe_distance analytic_point result; set distance [dval probe_distance_val]}] ||
        ![::single20::finite $distance]} {
        set coverage_ok 0
    } else {
        set worst_witness [expr {max($worst_witness,$distance)}]
        if {$distance > 1e-5*$scale} {set coverage_ok 0}
    }
}
::single20::assert endpoint_and_branch_coverage $coverage_ok "witnesses=[llength $witnesses] max_distance=$worst_witness limit=[expr {1e-5*$scale}]" numeric
::single20::finish
