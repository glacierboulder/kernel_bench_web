source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
lassign $::single20_case gap degrees rigid
set lower_second [expr {10.0+$gap}]
box first 10 10 10
box second $lower_second 0 0 10 10 10
explode second f
copy second_1 splitter
trotate splitter 0 5 5 0 1 0 $degrees
mksurface plane_support splitter
mkface splitter plane_support -100 100 -100 100
if {$rigid} {ttranslate first second splitter 17 -29 43}
bclearobjects
bcleartools
baddobjects first second splitter
set operation_error [catch {bfillds; bbuild result} operation_log]
set solids {}
catch {set solids [explode result so]}
if {[info exists ::single20_negative]} {
    switch $::single20_negative {
        missing {set solids [lrange $solids 0 end-1]}
        empty {set solids {}}
        shifted {foreach shape $solids {ttranslate $shape 1000 1000 1000}}
    }
}
::single20::assert operation_completed [expr {$operation_error == 0}] "error=$operation_error report=$operation_log"
::single20::assert four_solids [expr {[llength $solids] == 4}] "observed=[llength $solids] expected=4" numeric
set theta [expr {$degrees*acos(-1)/180.0}]
set slope [expr {tan($theta)}]
set intercept [expr {($lower_second-5*sin($theta))/cos($theta)}]
set first_crossing [expr {(10-$intercept)/$slope}]
set second_crossing [expr {($lower_second-$intercept)/$slope}]
if {$first_crossing <= 0 || $first_crossing >= 10 || $second_crossing <= 0 || $second_crossing >= 10} {
    error "splitter is outside the qualified four-solid analytic regime"
}
set first_wedge [expr {5.0*pow(10-$intercept,2)/$slope}]
set second_wedge [expr {5.0*pow($intercept+10*$slope-$lower_second,2)/$slope}]
set expected_volumes [lsort -real [list $first_wedge [expr {1000-$first_wedge}] $second_wedge [expr {1000-$second_wedge}]]]
set observed_volumes {}
set area 0.0
set validity_ok [expr {[llength $solids] == 4}]
foreach solid $solids {
    if {[catch {checkshape $solid} validity] || [string first "This shape seems to be valid" $validity] < 0} {
        set validity_ok 0
    }
    if {[catch {
        lappend observed_volumes [::single20::mass vprops $solid]
        set area [expr {$area+[::single20::mass sprops $solid]}]
    }]} {set validity_ok 0}
}
::single20::assert solid_validity $validity_ok "checked_solids=[llength $solids]"
set observed_volumes [lsort -real $observed_volumes]
set volume_ok [expr {[llength $observed_volumes] == 4}]
set worst_volume_error 0.0
if {$volume_ok} {
    foreach actual $observed_volumes expected $expected_volumes {
        set difference [expr {abs($actual-$expected)}]
        set worst_volume_error [expr {max($worst_volume_error,$difference)}]
        if {$difference > 1e-4} {set volume_ok 0}
    }
}
::single20::assert component_volumes $volume_ok "observed=$observed_volumes expected=$expected_volumes max_error=$worst_volume_error limit=1e-4" numeric
set expected_area [expr {1200+20*($first_crossing+10-$second_crossing)/cos($theta)}]
::single20::assert solid_area [expr {[llength $solids] == 4 && abs($area-$expected_area) <= 1e-3}] "observed=$area expected=$expected_area limit=1e-3" numeric
set centroid_ok 0
set centroid_error unknown
if {[llength $solids] == 4} {
    eval compound $solids solids_only
    if {![catch {vprops solids_only cx cy cz -full; set x [dval cx]; set y [dval cy]; set z [dval cz]}] &&
        [::single20::finite $x] && [::single20::finite $y] && [::single20::finite $z]} {
        set expected_x [expr {10+$gap/2.0+($rigid ? 17 : 0)}]
        set expected_y [expr {5+($rigid ? -29 : 0)}]
        set expected_z [expr {5+($rigid ? 43 : 0)}]
        set centroid_error [expr {sqrt(pow($x-$expected_x,2)+pow($y-$expected_y,2)+pow($z-$expected_z,2))}]
        set centroid_ok [expr {$centroid_error <= 1e-6}]
    }
}
::single20::assert preserved_centroid $centroid_ok "distance=$centroid_error limit=1e-6" numeric
::single20::finish
