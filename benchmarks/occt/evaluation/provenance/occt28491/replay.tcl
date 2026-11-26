pload MODELING
set here [file dirname [info script]]
foreach {tag dx} {original 0 left -0.01 right 0.01 translated 0 reversed 0 control 0} {
    restore [file join $here bug24094_face.brep] a
    plane p [expr {183.6+$dx}] 0 0 1 0 0 0 1 0
    mkface f p
    if {$tag eq "translated"} { ttranslate a f 12.5 -7 3 }
    if {$tag eq "control"} {
        plane cp 0 0 0 0 0 1
        mkface a cp -5 5 -3 3
        plane vp 0 0 0 1 0 0
        mkface f vp -15 15 -15 15
    }
    foreach opts {{} {-na} {-n2d2} {-n2d} {-n2d -na}} {
        if {$tag eq "reversed"} { bsection res f a {*}$opts } else { bsection res a f {*}$opts }
        set nb [nbshapes res]
        regexp {VERTEX\s*:\s*([0-9]+)} $nb _ v
        regexp {EDGE\s*:\s*([0-9]+)} $nb _ e
        set lp [lprops res]
        if {![regexp -nocase {mass\s*[:=]\s*([-+0-9.eE]+)} $lp _ length]} {
            puts "RAW_LPROPS $lp"; error "Missing length"
        }
        puts "MEASURE tag=$tag x=[expr {183.6+$dx}] options=($opts) V=$v E=$e L=$length"
    }
}
