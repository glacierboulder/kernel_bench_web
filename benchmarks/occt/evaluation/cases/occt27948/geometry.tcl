pload MODELING

proc measure_cut {shape} {
    upvar 1 $shape measured
    set counts {}
    set stats [uplevel 1 [list nbshapes $shape]]
    foreach kind {VERTEX EDGE WIRE FACE SHELL SOLID} {
        if {![regexp -line [format {^\s*%s\s*:\s*([0-9]+)} $kind] $stats _ n]} {
            error "Missing $kind: $stats"
        }
        lappend counts $n
    }
    foreach {prop cmd} {area sprops volume vprops} {
        set report [uplevel 1 [list $cmd $shape 1.e-6]]
        if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} $report _ value]} {
            error "Missing $prop: $report"
        }
        set $prop $value
    }
    set validation [uplevel 1 [list checkshape $shape]]
    set valid [string match {*This shape seems to be valid*} $validation]
    return [list $counts $area $volume $valid]
}

proc cut_trial {mode assets} {
    if {$mode eq "control"} {
        box a 0 0 0 6 5 4
        box b 3 -1 -1 5 7 6
    } else {
        restore [file join $assets bug27948_a.brep] a
        restore [file join $assets bug27948_b.brep] b
        switch -- $mode {
            original {}
            translated {ttranslate a b 3 -2 1}
            rotated {trotate a b 0 0 0 0 0 1 17}
            scaled {tscale a b 0 0 0 1.02}
            default {error "unknown trial $mode"}
        }
    }
    bcut result a b
    if {![isdraw result]} {error "cut did not return a measurable shape"}
    lassign [measure_cut result] counts area volume valid
    set topology [lrange $counts 2 end]
    if {$mode eq "control"} {
        set expected {6 6 1 1}
        set targetA 94.0
        set targetV 60.0
    } else {
        set expected {19 17 1 1}
        set s [expr {$mode eq "scaled" ? 1.02 : 1.0}]
        set targetA [expr {135.137*$s*$s}]
        set targetV [expr {40.573*$s*$s*$s}]
    }
    set ok [expr {$valid && $topology eq $expected && abs($area-$targetA) <= 0.015 && abs($volume-$targetV) <= 0.015}]
    puts "READING mode=$mode V,E,W,F,Sh,So=[join $counts ,] area_mm2=$area volume_mm3=$volume valid=$valid pass=$ok"
    return $ok
}
