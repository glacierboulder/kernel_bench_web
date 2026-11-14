pload MODELING
box a 10 10 10
box b 5 2 3 10 10 10
explode a f
explode b f
foreach {face1 face2 expected} {a_2 b_3 7 a_2 b_5 8 a_4 b_1 7 a_4 b_5 5 a_6 b_1 8 a_6 b_3 5} {
 set log [bopcurves $face1 $face2 -2d]
 set curves [lsort -unique [regexp -all -inline {\mc_[0-9]+\M} $log]]
 if {[llength $curves] != 1} {error "expected one straight intersection"}
 set measure [length [lindex $curves 0]]
 if {![regexp {is\s+([-+0-9.eE]+)} $measure all value] || abs($value-$expected)>1e-7} {error "incorrect intersection length"}
}
puts CASE_PASS
