pload MODELING
set ::fixture30760 [file join [file dirname [info script]] assets bug30760_shapes.brep]
proc count_30760 {stats kind} {
    if {![regexp -line [format {^\s*%s\s*:\s*([0-9]+)} $kind] $stats _ value]} {error "missing $kind"}
    return $value
}
proc mass_30760 {stats} {
    if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} $stats _ value]} {error "missing mass"}
    return $value
}
proc check_case {mode} {
    set ok 1
    foreach order {forward reverse} {
        restore $::fixture30760 model
        if {$mode eq "translated"} {ttranslate model 0.125 0 -0.0625}
        if {$mode eq "alternate"} {trotate model 0 0 0 0 0 1 90}
        explode model
        if {$mode eq "control"} {ttranslate model_2 20 10 10}
        bclearobjects
        bcleartools
        set a model_1
        set b model_2
        if {$order eq "reverse"} {set a model_2; set b model_1}
        baddobjects $a
        baddtools $b
        bfillds
        bbop overlap 0
        set stats [nbshapes overlap]
        set solids [count_30760 $stats SOLID]
        set faces [count_30760 $stats FACE]
        set volume [mass_30760 [vprops overlap]]
        set valid [string match {*This shape seems to be valid*} [checkshape overlap]]
        puts "$mode $order: solids=$solids faces=$faces volume=$volume valid=$valid"
        if {$mode eq "control"} {
            bbop united 1
            set unionSolids [count_30760 [nbshapes united] SOLID]
            set unionVolume [mass_30760 [vprops united]]
            set inputVolume [expr {[mass_30760 [vprops $a]] + [mass_30760 [vprops $b]]}]
            set unionValid [string match {*This shape seems to be valid*} [checkshape united]]
            puts "$mode $order: union_solids=$unionSolids union_volume=$unionVolume input_sum=$inputVolume"
            set ok [expr {$ok && $valid && $solids == 0 && $faces == 0 && abs($volume) < 1.e-12
                        && $unionValid && $unionSolids == 2 && abs($unionVolume - $inputVolume) < 1.e-7}]
        } else {
            set ok [expr {$ok && $valid && $solids == 1 && $faces == 14
                        && abs($volume - 0.000106046) < 1.e-8}]
        }
    }
    return $ok
}
