source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
restore [file join [file dirname [info script]] bug24429_s1.draw] first
restore [file join [file dirname [info script]] bug24429_s2.draw] second
set error_code [catch {intersect c first second} operation_log]
set prefix c
set limit 1e-6
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
set first_error [expr {abs(sqrt(pow($y-9.4,2)+pow($z-48,2))-0.2)}]
set rho [expr {sqrt(pow($x+59.268,2)+$y*$y)}]
set second_error [expr {abs(sqrt(pow($rho-20.480725087838248,2)+pow($z-47.2,2))-1)}]
        if {![::single20::finite $first_error] || ![::single20::finite $second_error]} {set support_ok 0; continue}
        set maximum [expr {max($maximum,$first_error,$second_error)}]
        if {$first_error>$limit || $second_error>$limit} {set support_ok 0}
    }
}
::single20::assert support $support_ok "max_distance=$maximum limit=$limit" numeric
set witnesses {}
foreach angle {0.0 0.7 1.5707963267948966 2.4 3.141592653589793 4.71238898038469} {
    set y [expr {9.4+0.2*cos($angle)}]
    set z [expr {48+0.2*sin($angle)}]
    foreach radial {-1 1} {
        set rho [expr {20.480725087838248+$radial*sqrt(max(0,1-pow($z-47.2,2)))}]
        foreach sign {-1 1} {
            set x [expr {-59.268+$sign*sqrt($rho*$rho-$y*$y)}]
            lappend witnesses [list $x $y $z]
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
