pload MODELING
set ::sectionAssets [file join [file dirname [info script]] assets]

proc support_gap {shape faces} {
    global $shape {*}$faces
    global support curve3d uvcurve lo hi u v xs ys zs xc yc zc
    set worst 0.0
    foreach face $faces {
        mksurface support $face
        foreach edge [explode $shape e] {
            mkcurve curve3d $edge
            mk2dcurve uvcurve $edge $face
            bounds curve3d lo hi
            for {set i 0} {$i <= 24} {incr i} {
                set t [expr {[dval lo]+([dval hi]-[dval lo])*$i/24.0}]
                2dcvalue uvcurve $t u v
                svalue support u v xs ys zs
                cvalue curve3d $t xc yc zc
                set dx [expr {[dval xs]-[dval xc]}]
                set dy [expr {[dval ys]-[dval yc]}]
                set dz [expr {[dval zs]-[dval zc]}]
                set distance [expr {sqrt($dx*$dx+$dy*$dy+$dz*$dz)}]
                if {$distance > $worst} {set worst $distance}
            }
        }
    }
    return $worst
}

proc check_case {mode} {
    global s1 s2 f1 f2 ts1 b1 b2 t ctrl planeCtr sec
    if {$mode eq "control"} {
        box f1 0 0 0 10 10 10
        plane planeCtr 0 0 5 0 0 1
        mkface f2 planeCtr -20 20 -20 20
        set lengths {10 10 10 10}
        set vertices 4
    } else {
        set assets $::sectionAssets
        restore [file join $assets bug32701s.brep] f1
        restore [file join $assets bug32701t.brep] t
        explode t f
        copy t_3 f2
        if {$mode eq "translated"} {ttranslate f1 f2 1 -2 3}
        if {$mode eq "alternate"} {trotate f1 f2 0 0 0 0 0 1 15}
        set lengths {113.155}
        set vertices 2
    }
    bsection sec f1 f2
    set edgeLengths {}
    foreach edge [explode sec e] {
        if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops $edge] _ length]} {error "Missing edge length"}
        lappend edgeLengths $length
    }
    set edgeLengths [lsort -real $edgeLengths]
    set nVertices [llength [explode sec v]]
    if {![regexp {Tolerance MAX=([-+0-9.eE]+)} [tolerance sec] _ maxTol]} {error "Missing section tolerance"}
    set valid [string match {*seems to be valid*} [checkshape sec]]
    set passing [expr {$valid && $nVertices==$vertices && [llength $edgeLengths]==[llength $lengths] && $maxTol<3e-5}]
    if {[llength $edgeLengths]==[llength $lengths]} {
        foreach actual $edgeLengths expected $lengths {
            if {abs($actual-$expected)>0.01} {set passing 0}
        }
    }
    set gap 0.0
    if {$mode ne "control" && [llength $edgeLengths]>0} {
        set gap [support_gap sec {f1 f2}]
        if {$gap>1e-6} {set passing 0}
    }
    puts "mode=$mode vertices=$nVertices lengths={$edgeLengths} tolerance=$maxTol support_gap=$gap valid=$valid verdict=[expr {$passing ? {pass} : {fail}}]"
    return $passing
}
