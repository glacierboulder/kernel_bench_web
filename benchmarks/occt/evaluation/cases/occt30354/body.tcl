pload MODELING
set inputs_30354 [file join [file dirname [info script]] assets]

proc check_case {mode} {
    if {$mode eq "control"} {
        plane horizontal 0 0 0 0 0 1
        plane vertical 0 0 0 1 0 0
        mkface f horizontal -2 2 -2 2
        mkface g vertical -2 2 -2 2
        set target 4.0
    } else {
        restore [file join $::inputs_30354 bug30354_Face_14.brep] f
        restore [file join $::inputs_30354 bug30354_vol_neg.brep] g
        set scale 1.0
        if {$mode eq "translated"} {ttranslate f 0.0001 0 0}
        if {$mode eq "alternate"} {
            set scale 1.25
            tscale f 0 0 0 $scale
            tscale g 0 0 0 $scale
        }
        set target [expr {$scale * 0.0067028841369758101}]
    }
    bclearobjects
    bcleartools
    baddobjects f
    baddtools g
    bfillds
    bbop result 4
    set valid [string match {*This shape seems to be valid*} [checkshape result]]
    set stats [nbshapes result -t]
    if {![regexp {EDGE\s*:\s*(\d+)} $stats _ edges] ||
        ![regexp {VERTEX\s*:\s*(\d+)} $stats _ vertices] ||
        ![regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops result] _ measured]} {
        error "missing section topology or length"
    }
    puts "$mode valid=$valid edges=$edges vertices=$vertices length=$measured target=$target"
    return [expr {$valid && $edges == 1 && $vertices == 2 && abs($measured-$target) < 1.e-7}]
}
