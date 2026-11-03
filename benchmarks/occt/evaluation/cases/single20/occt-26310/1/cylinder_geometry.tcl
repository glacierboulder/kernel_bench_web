source [file join [file dirname [info script]] .. .. assertions.tcl]
pload TOPTEST
set healthy [expr {$::single20_case eq "healthy"}]
if {$healthy} {
    pcylinder first 20 50
    pcylinder second 10 50
    ttranslate second 1000 0 0
    set expected_count 0
} else {
restore [file join [file dirname [info script]] OCC26310-b1.brep] first
restore [file join [file dirname [info script]] OCC26310-b2.brep] second
    set expected_count 4
}
if {$::single20_case eq "rigid"} {
    trotate first second 0 0 0 0 0 1 30
    ttranslate first second 17 -29 43
}
if {$::single20_case eq "swap"} {
    renamevar first held_first
    renamevar second first
    renamevar held_first second
}
set valid_inputs 1
foreach shape {first second} {
    set validity [checkshape $shape]
    if {[string first "This shape seems to be valid" $validity]<0} {set valid_inputs 0}
}
::single20::assert input_validity $valid_inputs "both_valid=$valid_inputs"
explode first f
explode second f
array set cylinder {}
foreach face {first_1 second_1} {
    mksurface support_$face $face
    set info [dump support_$face]
    if {![regexp {Origin\s*:\s*([-+0-9.eE]+),\s*([-+0-9.eE]+),\s*([-+0-9.eE]+)} $info unused ox oy oz] ||
        ![regexp {Axis\s*:\s*([-+0-9.eE]+),\s*([-+0-9.eE]+),\s*([-+0-9.eE]+)} $info unused dx dy dz] ||
        ![regexp {Radius\s*:\s*([-+0-9.eE]+)} $info unused radius]} {error "missing analytic cylinder coefficients"}
    set norm [expr {sqrt($dx*$dx+$dy*$dy+$dz*$dz)}]
    set cylinder($face) [list $ox $oy $oz [expr {$dx/$norm}] [expr {$dy/$norm}] [expr {$dz/$norm}] $radius]
    puts "CYLINDER $face $cylinder($face)"
}
set operation_error [catch {bopcurves first_1 second_1 -2d} operation_log]
set curves {}
for {set i 1} {$i<32} {incr i} {
    if {[string first "3d curve" [whatis c_$i]]<0} {break}
    lappend curves c_$i
}
if {[info exists ::single20_negative]} {
    switch $::single20_negative {
        empty {set curves {}}
        missing {set curves [lrange $curves 0 end-1]}
        shifted {foreach curve $curves {translate $curve 1000 1000 1000}}
    }
}
::single20::assert operation_completed [expr {$operation_error==0}] "error=$operation_error report=$operation_log"
::single20::assert branches [expr {[llength $curves]==$expected_count}] "curves=[llength $curves] expected=$expected_count error=$operation_error report=$operation_log" numeric
set maximum 0.0
set measured 0
set ok [expr {[llength $curves]==$expected_count}]
foreach curve $curves {
    bounds $curve low high
    set a [dval low]
    set b [dval high]
    for {set i 0} {$i<=32} {incr i} {
        cvalue $curve [expr {$a+($b-$a)*$i/32.0}] px py pz
        vertex sample [dval px] [dval py] [dval pz]
        foreach face {first_1 second_1} {
            lassign $cylinder($face) ox oy oz dx dy dz radius
            set x [expr {[dval px]-$ox}]
            set y [expr {[dval py]-$oy}]
            set z [expr {[dval pz]-$oz}]
            set along [expr {$x*$dx+$y*$dy+$z*$dz}]
            set value [expr {abs(sqrt(pow($x-$along*$dx,2)+pow($y-$along*$dy,2)+pow($z-$along*$dz,2))-$radius)}]
            if {![::single20::finite $value]} {set ok 0; continue}
            incr measured
            set maximum [expr {max($maximum,$value)}]
            if {$value>1e-6} {set ok 0}
        }
    }
}
::single20::assert support $ok "points=$measured maximum=$maximum absolute_limit=1e-6" numeric
set section_error [catch {bsection section first second} section_log]
set edges {}
catch {set edges [explode section e]}
set alone -1
catch {regexp {nb alone Vertices : ([-0-9.+eE]+)} [checksection section] unused alone}
set validity unavailable
set valid 0
catch {set validity [checkshape section]; set valid [expr {[string first "This shape seems to be valid" $validity]>=0}]}
set section_ok [expr {$section_error==0 && $valid && ($healthy ? [llength $edges]==0 : ([llength $edges]>0 && $alone==0))}]
::single20::assert section_closure $section_ok "edges=[llength $edges] alone=$alone valid=$valid healthy=$healthy error=$section_error" numeric
::single20::finish
