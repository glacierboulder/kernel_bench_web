source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
set here [file dirname [info script]]
set healthy [expr {$::single20_case eq "healthy"}]
if {$healthy} {
plane support 0 0 5 0 0 1
mkface first support -5 15 -5 15
box second 10 10 10
copy first witness_face
} else {
restore [file join $here bug28388_extKO.brep] input
explode input
copy input_2 first
copy input_1 second
copy first witness_face
set z_low 13.75
set z_high 20.75
set inner_at_low 32.0
set slope 0.0
set thickness 0.25
}
if {$::single20_case eq "rigid"} {
    trotate first second 0 0 0 0 0 1 30
    ttranslate first second 17 -29 43
}
set valid_inputs 1
foreach shape {first second} {
    set check [checkshape $shape]
    puts "INPUT_VALIDITY $shape $check"
    if {[string first "This shape seems to be valid" $check]<0} {set valid_inputs 0}
}
::single20::assert input_validity $valid_inputs "both_inputs_valid=$valid_inputs"
if {$::single20_case eq "swap"} {
    set operation_error [catch {bop second first; bopcommon result} operation_log]
} else {
    set operation_error [catch {bop first second; bopcommon result} operation_log]
}
if {[info exists ::single20_negative]} {
    switch $::single20_negative {
        empty {compound result}
        input_only {copy first result}
        shifted {ttranslate result 1000000 1000000 1000000}
    }
}
::single20::assert operation_completed [expr {$operation_error==0}] "error=$operation_error report=$operation_log"
set validity [checkshape result]
::single20::assert validity [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
set faces [explode result f]
set edges [explode result e]
set vertices [explode result v]
::single20::assert topology [expr {[llength $faces]==1 && [llength $edges]==4 && [llength $vertices]==4}] "faces=[llength $faces] edges=[llength $edges] vertices=[llength $vertices] expected=1,4,4" numeric
set area [::single20::mass sprops result]
set input_area [::single20::mass sprops first]
::single20::assert area_bounds [expr {$area>1e-7 && $area<=$input_area*(1+1e-4)}] "area=$area input_area=$input_area relative_limit=1e-4" numeric
mksurface witness_surface witness_face
bounds witness_surface u_low u_high v_low v_high
if {$healthy} {dset u_low -5 u_high 15 v_low -5 v_high 15}
set inside 0
set outside 0
set mismatch 0
set input_domain_ok 1
set maximum_inside 0.0
foreach uf {0.0 0.001 0.1 0.3 0.5 0.7 0.9 0.999 1.0} {
    foreach vf {0.0 0.001 0.1 0.3 0.5 0.7 0.9 0.999 1.0} {
        set u [expr {[dval u_low]+$uf*([dval u_high]-[dval u_low])}]
        set v [expr {[dval v_low]+$vf*([dval v_high]-[dval v_low])}]
        svalue witness_surface $u $v px py pz
        set x [dval px]
        set y [dval py]
        set z [dval pz]
        vertex original_point $x $y $z
        distmini input_distance original_point witness_face
        if {[dval input_distance_val]>1e-7} {set input_domain_ok 0; continue}
        if {$healthy} {
            set margin [expr {min($x,10-$x,$y,10-$y,$z,10-$z)}]
        } else {
            set radius [expr {sqrt($x*$x+$y*$y)}]
            set inner [expr {$inner_at_low+($z-$z_low)*$slope}]
            set margin [expr {min($z-$z_low,$z_high-$z,$radius-$inner,$inner+$thickness-$radius)}]
        }
        # Omit ambiguous boundary points based only on the analytic input geometry.
        if {abs($margin)<1e-4} {continue}
        if {$::single20_case eq "rigid"} {
            set theta [expr {acos(-1)/6}]
            set tx [expr {cos($theta)*$x-sin($theta)*$y+17}]
            set ty [expr {sin($theta)*$x+cos($theta)*$y-29}]
            set x $tx
            set y $ty
            set z [expr {$z+43}]
        }
        vertex witness $x $y $z
        set distance unknown
        set finite_distance 0
        if {![catch {distmini result_distance witness result; set distance [dval result_distance_val]}]} {
            set finite_distance [::single20::finite $distance]
        }
        if {$margin>0} {
            incr inside
            if {!$finite_distance || $distance>1e-5} {incr mismatch}
            if {$finite_distance} {set maximum_inside [expr {max($maximum_inside,$distance)}]}
        } else {
            incr outside
            if {!$finite_distance || $distance<=1e-5} {incr mismatch}
        }
    }
}
::single20::assert analytic_membership [expr {$input_domain_ok && $inside>=5 && $outside>=2 && $mismatch==0}] "inside=$inside outside=$outside mismatches=$mismatch input_domain=$input_domain_ok max_inside_distance=$maximum_inside limit=1e-5 boundary_guard=1e-4" numeric
::single20::finish
