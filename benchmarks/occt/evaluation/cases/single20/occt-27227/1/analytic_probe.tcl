source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
ptorus first 100 20
tcopy first second
trotate second 0 0 0 1 0 0 90
explode first f
explode second f
set error_code [catch {bopcurves first_1 second_1 -2d} operation_log]
set prefix c
set limit 1e-5
set curves {}
if {[string first "3d curve" [whatis $prefix]]>=0} {lappend curves $prefix}
for {set index 1} {$index<100} {incr index} {
    set name ${prefix}_$index
    if {[string first "3d curve" [whatis $name]]<0} {break}
    lappend curves $name
}
::single20::assert nonempty [expr {[llength $curves]>0}] "curves=[llength $curves] error=$error_code report=$operation_log" numeric
set support_ok [expr {[llength $curves]>0}]
set maximum 0.0
set edges {}
set index 0
foreach curve $curves {
    bounds $curve low high
    set a [dval low]
    set b [dval high]
    if {![::single20::finite $a] || ![::single20::finite $b] || $b<=$a} {set support_ok 0; continue}
    incr index
    mkedge edge_$index $curve $a $b
    lappend edges edge_$index
    for {set i 0} {$i<=64} {incr i} {
        set t [expr {$a+($b-$a)*$i/64.0}]
        cvalue $curve $t px py pz
        set x [dval px]
        set y [dval py]
        set z [dval pz]
set first_error [expr {abs(sqrt(pow(sqrt($x*$x+$y*$y)-100,2)+$z*$z)-20)}]
set second_error [expr {abs(sqrt(pow(sqrt($x*$x+$z*$z)-100,2)+$y*$y)-20)}]
        if {![::single20::finite $first_error] || ![::single20::finite $second_error]} {set support_ok 0; continue}
        set maximum [expr {max($maximum,$first_error,$second_error)}]
        if {$first_error>$limit || $second_error>$limit} {set support_ok 0}
    }
}
::single20::assert support $support_ok "max_distance=$maximum limit=$limit" numeric
set witnesses {}
foreach y {-20.0 -19.9 -10.0 0.0 10.0 19.9 20.0} {
    foreach radial {-1 1} {
        set rho [expr {100+$radial*sqrt(max(0,400-$y*$y))}]
        foreach sign {-1 1} {
            set x [expr {$sign*sqrt($rho*$rho-$y*$y)}]
            foreach plane {-1 1} {lappend witnesses [list $x $y [expr {$plane*$y}]]}
        }
    }
}
set coverage_ok [expr {[llength $edges]>0}]
set worst 0.0
if {[llength $edges]>0} {
    eval compound $edges result
    foreach witness $witnesses {
        eval vertex point_witness $witness
        distmini distance point_witness result
        set value [dval distance_val]
        if {![::single20::finite $value] || $value>$limit} {set coverage_ok 0}
        set worst [expr {max($worst,$value)}]
    }
}
::single20::assert coverage $coverage_ok "witnesses=[llength $witnesses] maximum=$worst limit=$limit" numeric
::single20::finish
