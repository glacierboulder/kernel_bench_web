pload MODELING
set here [file dirname [info script]]
restore [file join $here bug25890_f1.brep] f1
restore [file join $here bug25890_f2.brep] f2
ttranslate f1 10 20 30
ttranslate f2 10 20 30
bsection e f1 f2
puts [nbshapes e]
puts [checkshape e]
puts [lprops e]
set edges [explode e e]
if {[llength $edges] != 1} {error "expected one edge"}
mkcurve measured [lindex $edges 0]
bounds measured lo hi
set worst 0
for {set j 0} {$j <= 20} {incr j} {
 set t [expr {[dval lo]+([dval hi]-[dval lo])*$j/20.0}]
 cvalue measured $t px py pz
 vertex probe [dval px] [dval py] [dval pz]
 foreach face {f1 f2} {
  dset delta_val -1
  distmini delta probe $face
  set val [dval delta_val]
  if {$val < 0} {error "missing point to face distance"}
  if {$val > $worst} {set worst $val}
 }
}
puts "SUPPORT_MAX $worst"
if {$worst > 1e-5} {error "support mismatch"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [lprops e] full length] || abs($length-5.03636)>0.0001} {error "unexpected section length"}
if {![string match "*This shape seems to be valid*" [checkshape e]]} {error "invalid edge"}
puts TEST_DONE
