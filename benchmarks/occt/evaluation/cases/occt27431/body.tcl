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
        restore [file join $assets OCC13116_sh1.brep] b1
        restore [file join $assets OCC13116_sh2.brep] b2
        explode b1 f
        explode b2 f
        mksurface s1 b1_3
        mksurface s2 b2_1
        mkface f1 s1 0 6.283185307179586 -10 10
        mkface f2 s2
        ttranslate f2 0 0 0.02
        if {$mode eq "translated"} {ttranslate f1 f2 1 -2 3}
        if {$mode eq "alternate"} {trotate f1 f2 0 0 0 0 0 1 15}
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
    set passing [expr {$valid && $nVertices==$vertices && $maxTol<0.005}]
    if {$mode eq "control"} {
        if {[llength $edgeLengths]!=4} {set passing 0}
        foreach actual $edgeLengths expected $lengths {
            if {$actual eq "" || $expected eq ""} {set passing 0; break}
            if {abs($actual-$expected)>0.0005} {set passing 0}
        }
    } else {
        set total 0.0
        foreach length $edgeLengths {set total [expr {$total+$length}]}
        if {[llength $edgeLengths]!=2 || abs($total-125.8173)>0.02} {set passing 0}
    }
    set gap 0.0
    if {$mode ne "control" && [llength $edgeLengths]>0} {
        set gap [support_gap sec {f1 f2}]
        if {$gap>1e-5} {set passing 0}
    }
    puts "mode=$mode vertices=$nVertices lengths={$edgeLengths} tolerance=$maxTol support_gap=$gap valid=$valid verdict=[expr {$passing ? {pass} : {fail}}]"
    return $passing
}
