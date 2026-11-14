pload MODELING
puts "============"
puts "OCC27079"
puts "============"
puts ""
##################################################################
# Bad approximation of intersection curves with variable curvature
##################################################################

restore [file join [file dirname [info script]] bug27079_s3.draw] s3
restore [file join [file dirname [info script]] bug27079_s4.draw] s4
trim  ts3 s3 pi-pi/30 pi -5 -2
mkface f1 ts3
mkface f2 s4

ttranslate f1 1 2 3
ttranslate f2 1 2 3
bop f1 f2
bopsection result
puts [nbshapes result]
puts [checkshape result]
puts [vprops result]
puts [lprops result]


set top [nbshapes result]
set lengthLog [lprops result]
if {![regexp -line {^\s*EDGE\s*:\s*2\s*$} $top]} {error "EDGE_COUNT_MISMATCH"}
if {![string match "*This shape seems to be valid*" [checkshape result]]} {error "INVALID_RESULT"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} $lengthLog all value] || abs($value-8.5688)>0.001} {error "LENGTH_MISMATCH"}
set worst 0
set edges [explode result e]

foreach edge $edges {
mkcurve measured $edge
bounds measured lo hi
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
}
puts "SUPPORT_MAX $worst"
if {$worst > 1e-5} {error "support mismatch"}

puts CASE_PASS


