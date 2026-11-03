# Two planes have the analytic intersection P + t*(-sin(theta),cos(theta),0).
# The original and neighborhoods retain an unbounded face. The healthy control
# bounds both faces. All coordinates are in the original model's length units.
source [file join [file dirname [info script]] .. .. assertions.tcl]
pload TOPTEST
lassign $::single20_case ox oy oz theta bounds_mode
set nx [expr {cos($theta)}]
set ny [expr {sin($theta)}]
plane first_support $ox $oy $oz 0 0 1 1 0 0
plane second_support $ox $oy $oz $nx $ny 0 0 0 1
if {$bounds_mode eq "bounded"} {
    mkface first_face first_support -20 20 -20 20
    mkface second_face second_support -20 20 -20 20
} elseif {$bounds_mode eq "mixed"} {
    mkface first_face first_support -20 20 -20 20
    mkface second_face second_support
} else {
    mkface first_face first_support
    mkface second_face second_support
}
set operation_error [catch {bopcurves first_face second_face} operation_log]
set curves {}
for {set i 1} {$i <= 8} {incr i} {
    if {[catch {whatis c_$i} description] || [string first "3d curve" $description] < 0} {break}
    lappend curves c_$i
}
if {[info exists ::single20_negative]} {
    if {$::single20_negative eq "missing"} {set curves {}}
    if {$::single20_negative eq "shifted"} {
        line wrong_curve [expr {$ox + $nx}] [expr {$oy + $ny}] $oz [expr {-$ny}] $nx 0
        set curves {wrong_curve}
    }
    if {$::single20_negative eq "truncated" && [llength $curves] == 1} {
        trim wrong_curve [lindex $curves 0] 0 0.0001
        set curves {wrong_curve}
    }
}
::single20::assert operation_completed [expr {$operation_error == 0}] "error=$operation_error report=$operation_log"
::single20::assert branch_count [expr {[llength $curves] == 1}] "observed=[llength $curves] expected=1" numeric
set residual_ok [expr {[llength $curves] == 1}]
set span_ok $residual_ok
set worst 0.0
set lower 0.0
set upper 0.0
foreach curve $curves {
    if {[catch {bounds $curve lower_bound upper_bound; set lower [dval lower_bound]; set upper [dval upper_bound]}]} {
        set span_ok 0
    } elseif {![::single20::finite $lower] || ![::single20::finite $upper]} {
        set span_ok 0
    } elseif {$bounds_mode eq "unbounded"} {
        if {$lower > -1e10 || $upper < 1e10} {set span_ok 0}
    } elseif {$upper - $lower < 2.0} {
        set span_ok 0
    }
    foreach parameter {-1.0 0.0 1.0} {
        if {[catch {cvalue $curve $parameter px py pz; set x [dval px]; set y [dval py]; set z [dval pz]}]} {
            set residual_ok 0
            continue
        }
        if {![::single20::finite $x] || ![::single20::finite $y] || ![::single20::finite $z]} {
            set residual_ok 0
            continue
        }
        set plane_error [expr {max(abs($z-$oz), abs(($x-$ox)*$nx + ($y-$oy)*$ny))}]
        set worst [expr {max($worst, $plane_error)}]
        if {$plane_error > 1e-7} {set residual_ok 0}
    }
}
::single20::assert support_residual $residual_ok "max_distance=$worst limit=1e-7" numeric
::single20::assert domain_coverage $span_ok "lower=$lower upper=$upper mode=$bounds_mode" numeric
::single20::finish
