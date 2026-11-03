source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
lassign $::single20_case scale translated healthy
set ox [expr {$translated ? 17.0 : 0.0}]
set oy [expr {$translated ? -29.0 : 0.0}]
set oz [expr {$translated ? 43.0 : 0.0}]
if {$healthy} {
    sphere first_support 0 0 0 10
    plane second_support 0 0 0 0 0 1
    mkface first first_support
    mkface second second_support -20 20 -20 20
} else {
    restore [file join [file dirname [info script]] bug25890_f1.brep] first
    restore [file join [file dirname [info script]] bug25890_f2.brep] second
    if {$scale != 1} {tscale first second 0 0 0 $scale}
    if {$translated} {ttranslate first second $ox $oy $oz}
}
set operation_error [catch {bopcurves first second} operation_log]
set curves {}
for {set index 1} {$index<100} {incr index} {
    if {[string first "3d curve" [whatis c_$index]]<0} {break}
    lappend curves c_$index
}
if {[info exists ::single20_negative]} {
    switch $::single20_negative {
        missing {set curves [lrange $curves 0 end-1]}
        duplicate {lappend curves [lindex $curves 0]}
        shifted {foreach curve $curves {translate $curve 1000 0 0}}
    }
}
::single20::assert operation_completed [expr {$operation_error==0}] "error=$operation_error report=$operation_log"
::single20::assert nonempty [expr {[llength $curves]>0}] "segments=[llength $curves]" numeric
set intervals {}
set maximum 0.0
set support_ok [expr {[llength $curves]>0}]
set edges {}
set index 0
foreach curve $curves {
    bounds $curve low high
    set a [dval low]
    set b [dval high]
    if {![::single20::finite $a] || ![::single20::finite $b] || $b<=$a} {set support_ok 0; continue}
    set endpoint_parameters {}
    for {set i 0} {$i<=32} {incr i} {
        set parameter [expr {$a+($b-$a)*$i/32.0}]
        cvalue $curve $parameter px py pz
        set x [expr {([dval px]-$ox)/$scale}]
        set y [expr {([dval py]-$oy)/$scale}]
        set z [expr {([dval pz]-$oz)/$scale}]
        if {$healthy} {
            set error [expr {max(abs($z),abs(sqrt($x*$x+$y*$y)-10))}]
        } else {
            set linear [expr {2*(10.78010547359875-9)}]
            set quadratic [expr {13.286-2*10.78010547359875+9}]
            set discriminant [expr {$linear*$linear+4*$quadratic*($z-9)}]
            if {$discriminant<0} {set support_ok 0; continue}
            set t [expr {2*($z-9)/($linear+sqrt($discriminant))}]
            set expected_x [expr {240*(1-$t)*(1-$t)+2*241.8390097297814*$t*(1-$t)+242.526*$t*$t}]
            set error [expr {max(abs($x-$expected_x),abs($y))}]
            if {$t < -1e-6 || $t > 1+1e-6} {set support_ok 0}
            if {$i==0 || $i==32} {lappend endpoint_parameters $t}
        }
        if {![::single20::finite $error] || $error>1e-5} {set support_ok 0}
        set maximum [expr {max($maximum,$error)}]
    }
    if {!$healthy && [llength $endpoint_parameters]==2} {
        lassign [lsort -real $endpoint_parameters] t0 t1
        lappend intervals [list $t0 $t1]
    }
    incr index
    mkedge measured_edge_$index $curve $a $b
    lappend edges measured_edge_$index
}
::single20::assert analytic_support $support_ok "maximum_normalized_error=$maximum limit=1e-5" numeric
set coverage_ok [expr {[llength $curves]>0}]
set overlap_ok $coverage_ok
set cursor 0.0
set max_gap 0.0
set max_overlap 0.0
if {$healthy} {
    set coverage_ok [expr {[llength $curves]==1}]
    set overlap_ok $coverage_ok
} else {
    foreach interval [lsort -real -index 0 $intervals] {
        lassign $interval lo hi
        set max_gap [expr {max($max_gap,$lo-$cursor)}]
        set max_overlap [expr {max($max_overlap,$cursor-$lo)}]
        if {$lo>$cursor+1e-6 || $hi<=$lo} {set coverage_ok 0}
        if {$lo<$cursor-1e-6} {set overlap_ok 0}
        set cursor [expr {max($cursor,$hi)}]
    }
    if {abs($cursor-1)>1e-6 || [llength $intervals]!=[llength $curves]} {set coverage_ok 0}
}
::single20::assert complete_domain $coverage_ok "end=$cursor max_parameter_gap=$max_gap limit=1e-6 intervals=$intervals" numeric
::single20::assert no_duplicate_coverage $overlap_ok "max_parameter_overlap=$max_overlap limit=1e-6" numeric
set length 0.0
if {[llength $edges]>0} {eval compound $edges result; set length [::single20::mass lprops result]}
# Simpson integration of the explicit quadratic boundary, independent of OCCT.
set expected_length [expr {20*acos(-1)}]
if {!$healthy} {
    set sum 0.0
    for {set i 0} {$i<=1000} {incr i} {
        set t [expr {$i/1000.0}]
        set dx [expr {2*(241.8390097297814-240)*(1-$t)+2*(242.526-241.8390097297814)*$t}]
        set dz [expr {2*(10.78010547359875-9)*(1-$t)+2*(13.286-10.78010547359875)*$t}]
        set weight [expr {$i==0 || $i==1000 ? 1 : ($i%2 ? 4 : 2)}]
        set sum [expr {$sum+$weight*sqrt($dx*$dx+$dz*$dz)}]
    }
    set expected_length [expr {$sum/3000.0*$scale}]
}
::single20::assert boundary_length [expr {abs($length-$expected_length)<=1e-5*$scale}] "observed=$length expected=$expected_length limit=[expr {1e-5*$scale}]" numeric
::single20::finish
