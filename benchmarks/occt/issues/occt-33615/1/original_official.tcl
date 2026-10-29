set v4_dir [file dirname [info script]]
source [file join $v4_dir bootstrap.tcl]
source [file join $v4_dir official_upstream.tcl]
if {[catch {nbshapes result} v4_topology_info]} {
  set v4_topology_rc 1
} else {
  set v4_topology_rc 0
}
foreach {v4_id v4_entity v4_expected} {vertex_count VERTEX 5 edge_count EDGE 8 wire_count WIRE 5 face_count FACE 4} {
  set v4_pattern [format {%s +: +([-0-9.+eE]+)} $v4_entity]
  if {!$v4_topology_rc && [regexp $v4_pattern $v4_topology_info -> v4_observed]} {
    set v4_observed [expr {int($v4_observed)}]
    puts "M33615_ORIGINAL_${v4_entity}=$v4_observed expected=$v4_expected"
    stage3_assert [expr {$v4_observed == $v4_expected}] $v4_id "observed=$v4_observed expected=$v4_expected"
  } else {
    stage3_assert 0 $v4_id "not measured: nbshapes_error=$v4_topology_rc output={$v4_topology_info}"
  }
}
stage3_assert 1 official_oracle_completed {official topology test and named entity measurements completed}
v4_finish
