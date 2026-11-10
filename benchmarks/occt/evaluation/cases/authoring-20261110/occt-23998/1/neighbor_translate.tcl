set here [file dirname [info script]]
source [file join $here .. .. .. single20 assertions.tcl]
source [file join $here .. .. oracle_helpers.tcl]
set inputs [file normalize [file join $here .. .. .. .. .. issues occt-23998 1 public inputs]]
pload MODELING
restore [file join $inputs bug23998_draw.brep] b
ttranslate b 100 -50 25
explode b
bop b_1 b_2
bopsection result
explode result e
mkcurve c result_1
set span 1.0
puts "=== SHAPE ==="
set valid_log [checkshape result]
puts $valid_log
set shape_log [nbshapes result]
puts $shape_log
set mass_log [lprops result]
puts $mass_log
puts "=== SAMPLES ==="
set samples {}
for {set k 0} {$k<=1000} {incr k} {
 set t [expr {$span*$k/1000.0}]
 cvalue c $t px py pz
 lappend samples [list [dval px] [dval py] [dval pz]]
}


set mass [::author20261110::mass $mass_log]
::single20::assert shape_valid [expr {[string first "This shape seems to be valid" $valid_log]>=0}] topology_check
::single20::assert one_edge [expr {[::author20261110::count $shape_log EDGE]==1}] one_section_edge numeric
::single20::assert length [::author20261110::close $mass 67.026 0.002] "length=$mass expected=67.026" numeric
set polyline 0.0
set all_finite [expr {[llength $samples]==1001}]
set previous {}
foreach pt $samples {
 foreach value $pt {if {![::single20::finite $value]} {set all_finite 0}}
 if {[llength $previous]==3 && $all_finite} {
  lassign $pt x y z
  lassign $previous a b c
  set polyline [expr {$polyline+sqrt(($x-$a)*($x-$a)+($y-$b)*($y-$b)+($z-$c)*($z-$c))}]
 }
 set previous $pt
}
::single20::assert sampled_length [expr {$all_finite && [::author20261110::close $polyline $mass 0.02]}] "samples=[llength $samples] polyline=$polyline" numeric
lassign [lindex $samples 0] x y z
lassign [lindex $samples end] a b c
::single20::assert closed_curve [expr {$all_finite && sqrt(($x-$a)*($x-$a)+($y-$b)*($y-$b)+($z-$c)*($z-$c))<=0.002}] closure_distance numeric


# Sample trimmed edges, including their endpoints, against both bounded faces.
# Reset Draw distance variables before every call; failed extrema may not leave stale data.
set audit_edges [explode result e]
set audit_ok [expr {[llength $audit_edges]>0}]
set audit_worst 0.0
set audit_samples 0
set audit_mids {}
foreach audit_edge $audit_edges {
 mkcurve audit_curve $audit_edge
 bounds audit_curve audit_first audit_last
 set audit_lo [dval audit_first]
 set audit_hi [dval audit_last]
 if {![::single20::finite $audit_lo] || ![::single20::finite $audit_hi] || $audit_hi<=$audit_lo} {set audit_ok 0;continue}
 for {set audit_k 0} {$audit_k<=20} {incr audit_k} {
  set audit_t [expr {$audit_lo+($audit_hi-$audit_lo)*$audit_k/20.0}]
  cvalue audit_curve $audit_t audit_x audit_y audit_z
  set audit_px [dval audit_x]
  set audit_py [dval audit_y]
  set audit_pz [dval audit_z]
  if {![::single20::finite $audit_px] || ![::single20::finite $audit_py] || ![::single20::finite $audit_pz]} {set audit_ok 0;continue}
  if {$audit_k==10} {lappend audit_mids [list $audit_px $audit_py $audit_pz]}
  vertex audit_point $audit_px $audit_py $audit_pz
  foreach audit_face {b_1 b_2} {
   dset audit_distance_val -1
   distmini audit_distance audit_point $audit_face
   set audit_d [dval audit_distance_val]
   incr audit_samples
   if {![::single20::finite $audit_d] || $audit_d<0 || $audit_d>1e-5} {set audit_ok 0}
   if {[::single20::finite $audit_d] && $audit_d>$audit_worst} {set audit_worst $audit_d}
  }
 }
}
::single20::assert support_faces [expr {$audit_ok && $audit_samples==42*[llength $audit_edges]}] "samples=$audit_samples worst_distance=$audit_worst limit=1e-5" numeric

::single20::finish
