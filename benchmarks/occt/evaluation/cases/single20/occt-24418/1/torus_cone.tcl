# M24418 programmatic upstream case. Direct torus/cone equations measure
# support error. Independently computed horizontal circle intersections check
# both sides of the closed branch, including the torus inner radial sheet.
source [file join [file dirname [info script]] .. .. assertions.tcl]
pload TOPTEST
lassign $::single20_case ox oy oz swapped separated
ptorus torus_shape 25 24 90
plane cone_axis 20 20 10 0 0 1
pcone cone_shape cone_axis 10 8 40
ttranslate torus_shape $ox $oy $oz
ttranslate cone_shape $ox $oy $oz
if {$separated} {ttranslate cone_shape 1000 0 0}
explode torus_shape f
explode cone_shape f
mksurface torus_support torus_shape_1
mksurface cone_support cone_shape_1
trimu torus_domain torus_support 0 1.5707963267948966
trimv cone_domain cone_support 0 40.049968789001575
set first torus_domain
set second cone_domain
if {$swapped} {set first cone_domain; set second torus_domain}
set operation_error [catch {intersect section $first $second} operation_log]
set curves {}
if {![catch {whatis section} description] && [string first "3d curve" $description] >= 0} {
    lappend curves section
} else {
    for {set i 1} {$i <= 16} {incr i} {
        if {[catch {whatis section_$i} description] || [string first "3d curve" $description] < 0} {break}
        lappend curves section_$i
    }
}
if {[info exists ::single20_negative]} {
    switch $::single20_negative {
        missing {set curves {}}
        shifted {
            foreach curve $curves {translate $curve 0 0 1}
        }
        truncated {
            if {[llength $curves]} {
                set curve [lindex $curves 0]
                bounds $curve low high
                trim wrong_curve $curve [dval low] [expr {[dval low]+0.1*([dval high]-[dval low])}]
                set curves {wrong_curve}
            }
        }
    }
}
set presence_ok [expr {$separated ? [llength $curves] == 0 : [llength $curves] > 0}]
::single20::assert operation_completed [expr {$operation_error == 0}] "error=$operation_error report=$operation_log"
::single20::assert nonempty_result $presence_ok "curve_fragments=[llength $curves] separated=$separated" numeric
set residual_ok $presence_ok
set closure_ok $residual_ok
set worst_residual 0.0
set edges {}
set endpoint_nodes {}
array set degree {}
array set neighbors {}
foreach curve $curves {
    if {[catch {bounds $curve low high; set lower [dval low]; set upper [dval high]}] ||
        ![::single20::finite $lower] || ![::single20::finite $upper] || $upper <= $lower} {
        set residual_ok 0
        set closure_ok 0
        continue
    }
    set endpoints {}
    for {set i 0} {$i <= 64} {incr i} {
        set parameter [expr {$lower+($upper-$lower)*$i/64.0}]
        if {[catch {cvalue $curve $parameter px py pz; set x [dval px]; set y [dval py]; set z [dval pz]}] ||
            ![::single20::finite $x] || ![::single20::finite $y] || ![::single20::finite $z]} {
            set residual_ok 0
            continue
        }
        if {$i == 0 || $i == 64} {lappend endpoints [list $x $y $z]}
        set x [expr {$x-$ox}]
        set y [expr {$y-$oy}]
        set z [expr {$z-$oz}]
        set torus_error [expr {abs(sqrt(pow(sqrt($x*$x+$y*$y)-25,2)+$z*$z)-24)}]
        set cone_radius [expr {10-0.05*($z-10)}]
        set cone_error [expr {abs(sqrt(pow($x-20,2)+pow($y-20,2))-$cone_radius)/sqrt(1.0025)}]
        set worst_residual [expr {max($worst_residual,$torus_error,$cone_error)}]
        if {$torus_error > 2e-7 || $cone_error > 2e-7 || $z < 10-2e-7 || $z > 50+2e-7 || $x < -2e-7 || $y < -2e-7} {
            set residual_ok 0
        }
    }
    if {[llength $endpoints] != 2} {
        set closure_ok 0
    } else {
        set node_pair {}
        foreach point $endpoints {
            lassign $point x y z
            set matching -1
            for {set node 0} {$node < [llength $endpoint_nodes]} {incr node} {
                lassign [lindex $endpoint_nodes $node] nx ny nz
                set gap [expr {sqrt(pow($x-$nx,2)+pow($y-$ny,2)+pow($z-$nz,2))}]
                if {$gap <= 2e-7} {set matching $node; break}
            }
            if {$matching < 0} {
                set matching [llength $endpoint_nodes]
                lappend endpoint_nodes $point
                set degree($matching) 0
                set neighbors($matching) {}
            }
            incr degree($matching)
            lappend node_pair $matching
        }
        lassign $node_pair first_node second_node
        lappend neighbors($first_node) $second_node
        lappend neighbors($second_node) $first_node
    }
    set edge_name edge_[llength $edges]
    if {[catch {mkedge $edge_name $curve}]} {
        set closure_ok 0
    } else {
        lappend edges $edge_name
    }
}
::single20::assert support_residual $residual_ok "max_distance=$worst_residual limit=2e-7" numeric
set visited {}
if {[llength $endpoint_nodes]} {
    set pending {0}
    while {[llength $pending]} {
        set node [lindex $pending end]
        set pending [lrange $pending 0 end-1]
        if {[lsearch -exact $visited $node] >= 0} {continue}
        lappend visited $node
        if {$degree($node) != 2} {set closure_ok 0}
        foreach next_node $neighbors($node) {lappend pending $next_node}
    }
    if {[llength $visited] != [llength $endpoint_nodes]} {set closure_ok 0}
} elseif {!$separated} {
    set closure_ok 0
}
::single20::assert branch_closed $closure_ok "endpoint_nodes=[llength $endpoint_nodes] connected_nodes=[llength $visited] join_limit=2e-7" numeric
set coverage_ok $presence_ok
set witnesses 0
set worst_distance 0.0
if {!$separated && [llength $edges]} {
    eval compound $edges all_edges
    set center_distance [expr {sqrt(800.0)}]
    foreach z {21.0 23.5 23.9} {
        set cone_radius [expr {10-0.05*($z-10)}]
        foreach radial_sign {-1 1} {
            set rho [expr {25+$radial_sign*sqrt(576-$z*$z)}]
            if {$rho < abs($center_distance-$cone_radius) || $rho > $center_distance+$cone_radius} {continue}
            set along [expr {($rho*$rho-$cone_radius*$cone_radius+800.0)/(2*$center_distance)}]
            set across [expr {sqrt(max(0.0,$rho*$rho-$along*$along))}]
            foreach side {-1 1} {
                set x [expr {($along-$side*$across)/sqrt(2.0)+$ox}]
                set y [expr {($along+$side*$across)/sqrt(2.0)+$oy}]
                vertex witness $x $y [expr {$z+$oz}]
                incr witnesses
                if {[catch {distmini witness_distance witness all_edges; set distance [dval witness_distance_val]}] ||
                    ![::single20::finite $distance]} {
                    set coverage_ok 0
                } else {
                    set worst_distance [expr {max($worst_distance,$distance)}]
                    if {$distance > 2e-7} {set coverage_ok 0}
                }
            }
        }
    }
    if {$witnesses != 10} {error "analytic witness construction is incomplete"}
} elseif {!$separated} {
    set coverage_ok 0
}
::single20::assert analytic_coverage $coverage_ok "witnesses=$witnesses max_distance=$worst_distance limit=2e-7" numeric
::single20::finish
