source [file join [file dirname [info script]] .. .. assertions.tcl]
pload TOPTEST
lassign $::single20_case scale rigid separated
ptorus first 750 250 360
pcone second 200 0 2000
trotate second 0 0 0 1 0 0 90
ttranslate second 0 1000 0
if {$separated} {ttranslate second 0 10000 0}
if {$scale!=1} {tscale first second 0 0 0 $scale}
if {$rigid} {
    trotate first second 0 0 0 0 0 1 90
    ttranslate first second 17 -29 43
}
set inputs_valid 1
foreach shape {first second} {
    set validity [checkshape $shape]
    if {[string first "This shape seems to be valid" $validity]<0} {set inputs_valid 0}
}
::single20::assert input_validity $inputs_valid "both_valid=$inputs_valid"
set error_code [catch {bcut result first second} operation_log]
if {[info exists ::single20_negative]} {
    switch $::single20_negative {
        unchanged {copy first result}
        empty {compound result}
        shifted {ttranslate result 10000 10000 10000}
    }
}
::single20::assert operation_completed [expr {$error_code==0}] "error=$error_code report=$operation_log"
set validity unavailable
catch {set validity [checkshape result]}
::single20::assert shape_valid [expr {[string first "This shape seems to be valid" $validity]>=0}] "validity=$validity"
set solids {}
catch {compound result measured_result; set solids [explode measured_result so]}
::single20::assert one_solid [expr {[llength $solids]==1}] "solids=[llength $solids] expected=1" numeric
set volume unknown
set volume_ok 0
set expected [expr {$separated ? 2*pow(acos(-1),2)*750*250*250 : 879203614.534149}]
set expected [expr {$expected*pow($scale,3)}]
set volume_limit [expr {pow($scale,3)}]
if {![catch {vprops result 1e-10 -full} properties] && [regexp {Mass\s*:\s*([-+0-9.eE]+)} $properties unused volume] && [::single20::finite $volume]} {
    set volume_ok [expr {abs($volume-$expected)<=$volume_limit}]
}
::single20::assert analytic_volume $volume_ok "observed=$volume expected=$expected absolute_limit=$volume_limit integration_epsilon=1e-10" numeric
foreach id {kept_positive kept_negative removed_positive removed_negative} x {750 -750 0 0} y {0 0 750 -750} {
    set expected_state [expr {$separated || [string first "kept" $id]==0 ? "IN" : "OUT"}]
    set x [expr {$x*$scale}]
    set y [expr {$y*$scale}]
    set z 0
    if {$rigid} {
        set saved_x $x
        set x [expr {17-$y}]
        set y [expr {$saved_x-29}]
        set z 43
    }
    point witness $x $y $z
    set state unavailable
    set ok 0
    if {[llength $solids]==1} {
        set state [bclassify [lindex $solids 0] witness 1e-7]
        set ok [regexp "\\m${expected_state}\\M" $state]
    }
    ::single20::assert $id $ok "point=($x,$y,$z) expected=$expected_state observed=$state"
}
::single20::finish
