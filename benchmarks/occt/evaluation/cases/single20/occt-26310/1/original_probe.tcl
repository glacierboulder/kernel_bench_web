source [file join [file dirname [info script]] .. .. assertions.tcl]
pload TOPTEST
restore [file join [file dirname [info script]] OCC26310-b1.brep] first
restore [file join [file dirname [info script]] OCC26310-b2.brep] second
explode first f
explode second f
set operation_error [catch {bopcurves first_1 second_1 -2d} operation_log]
set curves {}
for {set i 1} {$i<32} {incr i} {
    if {[string first "3d curve" [whatis c_$i]]<0} {break}
    lappend curves c_$i
}
::single20::assert branches [expr {[llength $curves]==4}] "curves=[llength $curves] expected=4 error=$operation_error report=$operation_log" numeric
set maximum 0.0
set measured 0
set ok [expr {[llength $curves]==4}]
foreach curve $curves {
    bounds $curve low high
    set a [dval low]
    set b [dval high]
    for {set i 0} {$i<=32} {incr i} {
        cvalue $curve [expr {$a+($b-$a)*$i/32.0}] px py pz
        vertex sample [dval px] [dval py] [dval pz]
        foreach face {first_1 second_1} {
            if {[catch {distmini distance sample $face; set value [dval distance_val]}] || ![::single20::finite $value]} {set ok 0; continue}
            incr measured
            set maximum [expr {max($maximum,$value)}]
            if {$value>1e-6} {set ok 0}
        }
    }
}
::single20::assert support $ok "points=$measured maximum=$maximum absolute_limit=1e-6" numeric
::single20::finish
