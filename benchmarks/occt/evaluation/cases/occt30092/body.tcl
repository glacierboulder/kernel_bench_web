pload MODELING
set assets_30092 [file join [file dirname [info script]] assets]
proc check_case {mode} {
    if {$mode eq "control"} {
        plane p 0 0 0 0 0 1
        mkface f p -10 10 -10 10
        plane q 0 0 0 1 0 0
        mkface g q -10 10 -10 10
        bsection result f g
        set expected {2 1 20}
    } else {
        restore [file join $::assets_30092 bug26795_c.brep] c
        explode c f
        line l 20004.7983876926 2164.22470816234 210.858020395251 -0.716336050762455 0.65536108806844 0.239508886314894
        set half [expr {$mode eq "alternate" ? 0.21 : 0.2}]
        mkedge e l [expr {-$half}] $half
        settolerance e 0.04
        if {$mode eq "translated"} {ttranslate c_1 c_2 e 4 -2 1}
        bclearobjects
        bcleartools
        baddobjects c_2
        baddtools e
        bfillds
        bsplit c_2
        bclearobjects
        bcleartools
        baddobjects e c_1
        baddtools c_2
        bfillds
        bbop result 4
        set expected {5 4 1250.44}
    }
    set counts [nbshapes result]
    if {![regexp {VERTEX\s*:\s*([0-9]+)} $counts _ vertices] ||
        ![regexp {EDGE\s*:\s*([0-9]+)} $counts _ edges] ||
        ![regexp {Mass\s*:\s*([0-9.eE+-]+)} [lprops result] _ length]} {
        error "missing section geometry"
    }
    set valid [string match {*This shape seems to be valid*} [checkshape result]]
    puts "$mode vertices=$vertices edges=$edges length=$length valid=$valid"
    lassign $expected nv ne target
    return [expr {$valid && $vertices==$nv && $edges==$ne && abs($length-$target)<0.1}]
}
