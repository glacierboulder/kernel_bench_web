pload MODELING
set ::filletAsset [file join [file dirname [file normalize [info script]]] assets corner.brep]
proc check_case {mode} {
    global a r a_1
    if {$mode eq "control"} {
        box a 0.2 0.2 0.2
        set expected [expr {6*0.2**2-2*0.2*0.01+0.2*0.01*acos(-1)/2-2*0.01**2*(1-acos(-1)/4)}]
    } else {
        restore $::filletAsset a
        if {$mode eq "translated"} {ttranslate a 0.002 -0.003 0.004}
        if {$mode eq "alternate"} {trotate a 0 0 0 0 0 1 15}
        set expected 0.220328
    }
    if {![string match {*seems to be valid*} [checkshape a]] || [llength [explode a E]] != 12} {error "invalid fixture"}
    if {[catch {fillet r a 0.01 a_1} why]} {puts "fillet did not produce a result: $why"; return 0}
    set msg [sprops r]
    if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} $msg -> area]} {error "missing area"}
    set faces [llength [explode r F]]
    set valid [string match {*seems to be valid*} [checkshape r]]
    puts "area=$area expected=$expected faces=$faces valid=$valid"
    return [expr {$valid && $faces==7 && abs($area-$expected)<=1e-5}]
}
