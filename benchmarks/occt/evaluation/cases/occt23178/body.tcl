pload MODELING
proc check_case {mode} {
    global s1 s2 f1 f2 res u1 u2
    set dx [expr {$mode eq "translated" ? 10 : 0}]
    cylinder s1 [expr {4.999999999813+$dx}] 1.35836143386791 0.20975890778078 -1 0 0 0 0 1 10
    cylinder s2 [expr {9.999999999813+$dx}] 9.1401960568287 0.11837300583107 0 -0.75870713028692 0.651431877061437 0 -0.651431877061437 -0.75870713028692 5
    set half [expr {$mode eq "alternate" ? 55 : 35}]
    mkface f1 s1 0 2*pi [expr {-$half}] $half
    mkface f2 s2 0 2*pi [expr {-$half}] $half
    if {$mode eq "control"} {ttranslate f2 100 100 100}
    bsection res f1 f2
    set count [llength [explode res e]]
    set length -1
    regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops res] _ length
    set maxDist 0
    foreach edge [explode res e] {
        mkcurve curve $edge
        bounds curve u1 u2
        foreach surface {s1 s2} {
            set report [xdistcs curve $surface u1 u2 33]
            set samples [regexp -all -inline {D=([-+0-9.eE]+)} $report]
            if {[llength $samples]<66} {error "Incomplete surface distance samples"}
            foreach {_ dist} $samples {if {$dist > $maxDist} {set maxDist $dist}}
        }
    }
    set ok [expr {$mode eq "control" ? $count==0 && $length==0 : $count==6 && abs($length-79.4278)<0.005 && $maxDist<=2.0e-7}]
    puts "mode=$mode edges=$count length=$length max_distance=$maxDist verdict=[expr {$ok ? {pass} : {fail}}]"
    return $ok
}
