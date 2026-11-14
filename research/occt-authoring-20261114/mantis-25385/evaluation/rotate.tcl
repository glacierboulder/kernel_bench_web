pload MODELING
puts "============"
puts "OCC25385"
puts "============"
puts ""
#######################################################################
# steep increase in tolerance by intersection
#######################################################################

restore [file join [file dirname [info script]] bug25385_shell2.brep] s


plane p 28.5 0 0 1 0 0 0 1 0
mkface f p
trotate s 0 0 0 0 0 1 17
trotate f 0 0 0 0 0 1 17
puts TOL_BEFORE_DUMP; puts [dump s]
bop s f
puts TOL_AFTER_DUMP; puts [dump s]; puts TOL_END_DUMP
bopsection r
copy r result
puts [nbshapes result]
puts [checkshape result]
puts [vprops result]
puts [lprops result]


set top [nbshapes result]
set lengthLog [lprops result]
if {![regexp -line {^\s*EDGE\s*:\s*14\s*$} $top]} {error "EDGE_COUNT_MISMATCH"}
if {![string match "*This shape seems to be valid*" [checkshape result]]} {error "INVALID_RESULT"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} $lengthLog all value] || abs($value-36.2401)>0.001} {error "LENGTH_MISMATCH"}
set worst 0
set edges [explode result e]

foreach edge $edges {
mkcurve measured $edge
bounds measured lo hi
for {set j 0} {$j <= 20} {incr j} {
 set t [expr {[dval lo]+([dval hi]-[dval lo])*$j/20.0}]
 cvalue measured $t px py pz
 vertex probe [dval px] [dval py] [dval pz]
 foreach face {s f} {
  dset delta_val -1
  distmini delta probe $face
  set val [dval delta_val]
  if {$val < 0} {error "missing point to face distance"}
  if {$val > $worst} {set worst $val}
 }
}
}
puts "SUPPORT_MAX $worst"
if {$worst > 0.000504} {error "support mismatch"}

puts CASE_PASS



