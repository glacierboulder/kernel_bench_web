source [file join [file dirname [info script]] .. .. assertions.tcl]
pload TOPTEST
lassign $::single20_case variant radius rigid separated
set here [file dirname [info script]]
restore [file join $here inputs first-${variant}.brep] first
restore [file join $here inputs second-${variant}.brep] second
set angle_pi [expr {acos(-1)}]
set pitch1 [expr {2*$angle_pi*50*tan(2.278524728621996*$angle_pi/180)}]
set pitch2 [expr {2*$angle_pi*50*tan((2.278524728621996+5.724061592216415)*$angle_pi/180)}]
if {$separated} {ttranslate second 0 0 1000}
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
proc volume {shape} {
    set report [uplevel #0 [list vprops $shape 1e-10 -full]]
    if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} $report unused value] || ![::single20::finite $value]} {
        error "missing finite adaptive volume"
    }
    return $value
}
set input_volume [expr {[volume first]+[volume second]}]
set error_code [catch {bfuse result first second} operation_log]
if {[info exists ::single20_negative]} {
    switch $::single20_negative {
        unchanged {compound first second result}
        empty {compound result}
        shifted {ttranslate result 10000 10000 10000}
    }
}
::single20::assert operation_completed [expr {$error_code==0}] "error=$error_code report=$operation_log"
set validity [checkshape result]
::single20::assert shape_valid [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
set solids [explode result so]
set expected_solids [expr {$separated ? 2 : 1}]
::single20::assert solid_count [expr {[llength $solids]==$expected_solids}] "solids=[llength $solids] expected=$expected_solids" numeric
set removed [expr {$input_volume-[volume result]}]
set expected_removed [expr {$separated ? 0.0 : (4.0/3.0)*pow($radius,3)*tan(5.724061592216415*$angle_pi/360)}]
::single20::assert overlap_volume [expr {abs($removed-$expected_removed)<=0.01}] "observed=$removed ideal_cap_wedge=$expected_removed absolute_limit=0.01 integration_epsilon=1e-10" numeric
set witness_index 0
foreach z [list [expr {$pitch1/2}] [expr {$pitch1+3.5*$pitch2+($separated ? 1000 : 0)}]] {
    incr witness_index
    set x -50
    set y 0
    if {$rigid} {set x 17; set y -79; set z [expr {$z+43}]}
    point probe $x $y $z
    set contained 0
    foreach solid $solids {
        if {[regexp {\mIN\M} [bclassify $solid probe 1e-7]]} {set contained 1}
    }
    ::single20::assert kept_tube_$witness_index $contained "point=($x,$y,$z) retained=$contained"
}
set section_error [catch {bsection section first second} section_log]
set edges {}
catch {set edges [explode section e]}
set alone -1
catch {regexp {nb alone Vertices : ([-0-9.+eE]+)} [checksection section] unused alone}
set section_ok [expr {$section_error==0 && ($separated ? [llength $edges]==0 : ([llength $edges]>0 && $alone==0))}]
::single20::assert closed_section $section_ok "edges=[llength $edges] alone=$alone separated=$separated error=$section_error" numeric
::single20::finish
