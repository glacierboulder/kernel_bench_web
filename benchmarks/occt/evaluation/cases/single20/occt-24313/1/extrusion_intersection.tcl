source [file join [file dirname [info script]] .. .. assertions.tcl]
pload TOPTEST
lassign $::single20_case ox oy oz radius angle surface_kind
set nx [expr {cos($angle)}]
set ny [expr {sin($angle)}]
if {$surface_kind eq "extrusion"} {
    circle basis $ox $oy $oz 0 0 1 1 0 0 $radius
    extsurf cylinder_support basis 0 0 1
} else {
    cylinder cylinder_support $ox $oy $oz 0 0 1 $radius
}
plane plane_support $ox $oy $oz $nx $ny 0 0 0 1
mkface cylinder_face cylinder_support
mkface plane_face plane_support
set operation_error [catch {bopcurves cylinder_face plane_face} operation_log]
set curves {}
for {set i 1} {$i <= 8} {incr i} {
    if {[catch {whatis c_$i} description] || [string first "3d curve" $description] < 0} {break}
    lappend curves c_$i
}
if {[info exists ::single20_negative]} {
    switch $::single20_negative {
        missing {set curves [lrange $curves 0 0]}
        shifted {
            line wrong_curve $ox $oy $oz 0 0 1
            set curves [list wrong_curve wrong_curve]
        }
        duplicate {set curves [list [lindex $curves 0] [lindex $curves 0]]}
        truncated {
            if {[llength $curves] == 2} {
                trim wrong_curve [lindex $curves 0] 0 0.0001
                set curves [list wrong_curve [lindex $curves 1]]
            }
        }
    }
}
::single20::assert operation_completed [expr {$operation_error == 0}] "error=$operation_error report=$operation_log"
::single20::assert branch_count [expr {[llength $curves] == 2}] "observed=[llength $curves] expected=2" numeric
set residual_ok [expr {[llength $curves] == 2}]
set span_ok $residual_ok
set positive 0
set negative 0
set worst 0.0
foreach curve $curves {
    if {[catch {bounds $curve lower_bound upper_bound; set lower [dval lower_bound]; set upper [dval upper_bound]}]} {
        set span_ok 0
    } elseif {![::single20::finite $lower] || ![::single20::finite $upper] || $lower > -1e10 || $upper < 1e10} {
        set span_ok 0
    }
    foreach parameter {-11.0 0.0 11.0} {
        if {[catch {cvalue $curve $parameter px py pz; set x [dval px]; set y [dval py]; set z [dval pz]}]} {
            set residual_ok 0
            continue
        }
        if {![::single20::finite $x] || ![::single20::finite $y] || ![::single20::finite $z]} {
            set residual_ok 0
            continue
        }
        set dx [expr {$x-$ox}]
        set dy [expr {$y-$oy}]
        set distance [expr {max(abs(sqrt($dx*$dx+$dy*$dy)-$radius), abs($dx*$nx+$dy*$ny))}]
        set worst [expr {max($worst, $distance)}]
        if {$distance > 1e-7} {set residual_ok 0}
        set side [expr {-$dx*$ny+$dy*$nx}]
        if {abs($side-$radius) <= 1e-7} {set positive 1}
        if {abs($side+$radius) <= 1e-7} {set negative 1}
    }
}
::single20::assert support_residual $residual_ok "max_distance=$worst limit=1e-7" numeric
::single20::assert domain_coverage [expr {$span_ok && $positive && $negative}] "unbounded=$span_ok positive_generator=$positive negative_generator=$negative" numeric
::single20::finish
