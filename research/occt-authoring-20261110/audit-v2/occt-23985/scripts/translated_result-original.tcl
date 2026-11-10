set here [file dirname [info script]]
source [file join $here .. .. .. single20 assertions.tcl]
source [file join $here .. .. oracle_helpers.tcl]
set inputs [file normalize [file join $here .. .. .. .. .. issues occt-23985 1 public inputs]]
pload MODELING
restore [file join $inputs bug23985_b1_draw.brep] a
restore [file join $inputs bug23985_b2_draw.brep] b

bsection result a b
ttranslate result 10000 10000 10000
set valid_log [checkshape result]
puts $valid_log
set shape_log [nbshapes result]
puts $shape_log
set mass_log [lprops result]
puts $mass_log


set mass [::author20261110::mass $mass_log]
::single20::assert shape_valid [expr {[string first "This shape seems to be valid" $valid_log]>=0}] topology_check
::single20::assert edge_count [expr {[::author20261110::count $shape_log EDGE]==2}] expected_edges=2 numeric
::single20::assert section_length [::author20261110::close $mass 2000 0.002] "length=$mass expected=2000" numeric


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
  foreach audit_face {a b} {
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
set audit_distinct 0
if {[llength $audit_mids]==2} {
 lassign [lindex $audit_mids 0] audit_x1 audit_y1 audit_z1
 lassign [lindex $audit_mids 1] audit_x2 audit_y2 audit_z2
 set audit_distinct [expr {sqrt(($audit_x1-$audit_x2)*($audit_x1-$audit_x2)+($audit_y1-$audit_y2)*($audit_y1-$audit_y2)+($audit_z1-$audit_z2)*($audit_z1-$audit_z2))>1e-4}]
}
::single20::assert distinct_branches $audit_distinct two_spatially_distinct_branches numeric

::single20::finish
