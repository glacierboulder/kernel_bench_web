pload MODELING
restore [file join [file dirname [info script]] bug24811_e1.brep] a
restore [file join [file dirname [info script]] bug24811_e2.brep] b
trotate a 0 0 0 0 0 1 17
trotate b 0 0 0 0 0 1 17
bop a b
bopcut result
puts "PARTS [llength [explode result]]"
puts [nbshapes result]
puts [checkshape result]
puts [vprops result]
puts [lprops result]


set top [nbshapes result]
set lengthLog [lprops result]
if {![regexp -line {^\s*EDGE\s*:\s*4\s*$} $top]} {error "EDGE_COUNT_MISMATCH"}
if {![string match "*This shape seems to be valid*" [checkshape result]]} {error "INVALID_RESULT"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} $lengthLog all value] || abs($value-3.28963)>0.001} {error "LENGTH_MISMATCH"}
if {[llength [explode result]] != 4} {error "PART_COUNT_MISMATCH"}
set parts [explode result e]
set worst 0
foreach edge $parts {
 mkcurve measured $edge
 bounds measured lo hi
 for {set k 0} {$k<=10} {incr k} {
  cvalue measured [expr {[dval lo]+([dval hi]-[dval lo])*$k/10.0}] px py pz
  vertex probe [dval px] [dval py] [dval pz]
  dset delta_val -1
  distmini delta probe a
  set val [dval delta_val]
  if {$val<0 || $val>1e-6} {error "curve support mismatch"}
  if {$val>$worst} {set worst $val}
 }
}
puts "SUPPORT_MAX $worst"
foreach {x y} {0 1 0.0202691578002498 0.999794559518151} {
 vertex expected_point $x $y 0
 trotate expected_point 0 0 0 0 0 1 17
 dset point_distance_val -1
 distmini point_distance expected_point result
 set gap [dval point_distance_val]
 if {$gap < 0 || $gap > 1e-6} {error "missing expected intersection point"}
}
puts CASE_PASS


