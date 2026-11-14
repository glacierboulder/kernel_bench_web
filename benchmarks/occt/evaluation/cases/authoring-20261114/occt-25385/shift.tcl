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
ttranslate s 1 2 3
ttranslate f 1 2 3
set preTolerance [dump s]
bop s f
set postTolerance [dump s]
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


proc maxShapeTolerance {dumpText} {
  set maximum -1
  foreach {match value} [regexp -all -inline {Tolerance\s*:\s*([-+0-9.eE]+)} $dumpText] {
    set maximum [expr {max($maximum,$value)}]
  }
  return $maximum
}
set before [maxShapeTolerance $preTolerance]
set after [maxShapeTolerance $postTolerance]
if {$before <= 0 || $after <= 0 || $after - $before > 0.0001 + 0.0001 * $before} {error "TOLERANCE_INFLATION $before $after"}
puts TEST_DONE
