pload MODELING
set here [file dirname [info script]]
restore [file join [file dirname [info script]] bug25952_shape.brep] q


explode q
copy q_1 b1
copy q_2 b2
set info [bopcurves b1 b2 -2d]
puts $info
set curves [lsort -unique [regexp -all -inline {\mc_[0-9]+\M} $info]]
puts "CURVES [llength $curves]"
foreach c $curves {
 set measurement [length $c]
 puts $measurement
 bounds $c lo hi
 set worst 0
 for {set k 0} {$k <= 20} {incr k} {
  set t [expr {[dval lo]+([dval hi]-[dval lo])*$k/20.0}]
  cvalue $c $t px py pz
  vertex probe [dval px] [dval py] [dval pz]
  foreach face {b1 b2} {
   dset dprobe_val -1
   distmini dprobe probe $face
   set distance [dval dprobe_val]
   if {$distance < 0} {error "missing distance"}
   if {$distance > $worst} {set worst $distance}
  }
 }
 puts "SUPPORT $c $worst"
}
puts PUBLIC_REPRO_COMPLETE
