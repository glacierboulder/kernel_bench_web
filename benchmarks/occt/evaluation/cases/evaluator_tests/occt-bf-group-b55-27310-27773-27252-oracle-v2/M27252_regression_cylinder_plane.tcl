# BF_CASE_ID: M27252_regression_cylinder_plane
set bf_case_dir [file dirname [file normalize [info script]]]
set bf_private_root [file normalize [file join $bf_case_dir .. ..]]
set bf_stage_data_root [file normalize [file join $bf_case_dir .. .. .. ..]]
set bf_frozen_data_root [file normalize [file join $bf_case_dir .. .. cases bundle]]
set bf_data_root {}
if {[file isdir [file join $bf_stage_data_root issues]]} {
  set bf_data_root $bf_stage_data_root
} elseif {[file isdir [file join $bf_frozen_data_root issues]]} {
  set bf_data_root $bf_frozen_data_root
}
if {$bf_data_root eq {}} { error "locked public input root not found" }
set bf_data_dir [file join $bf_data_root issues occt-27252 1 public inputs]
set imagedir [file join $bf_case_dir images]; file mkdir $imagedir
set test_image {M27252_regression_cylinder_plane}
proc locate_data_file {name} {
  if {![regexp {^[A-Za-z0-9_.-]+$} $name]} { error "unlocked data name" }
  set path [file join $::bf_data_dir $name]
  if {![file isfile $path]} { error "locked input missing: $name" }
  return $path
}
source [file join $bf_private_root evaluator_assets occt-bf-group-b55-27310-27773-27252-oracle-v2 draw_pure_display_noop.tcl]
puts "BF_HARNESS_CASE=M27252_regression_cylinder_plane"
pload TOPTEST
puts "BF_TOPTEST_LOADED=1"
set bf_source_rc [catch {source [file join $bf_private_root evaluator_assets occt-bf-group-b55-27310-27773-27252-oracle-v2 tests m27252_regression.tcl]} bf_source_message bf_source_options]
puts "BF_SOURCE_RC=$bf_source_rc"
if {$bf_source_rc != 0} { puts "BF_SOURCE_ERROR=$bf_source_message" }
foreach var {Toler NbCurv GoodNbCurv ExpTol log} {
  if {[info exists $var]} { puts "BF_VAR_${var}=[set $var]" }
}
if {[info exists log]} {
  puts "BF_OFFICIAL_BOP_LOG_BEGIN"
  puts $log
  puts "BF_OFFICIAL_BOP_LOG_END"
}
if {"M27252_regression_cylinder_plane" eq "M27773"} {
  set bf_vertex_rc [catch {explode result v} bf_vertex_message]
  puts "BF_VERTEX_COORDS_BEGIN"
  if {$bf_vertex_rc == 0} { puts [getcoords result_1 result_2] }
  puts "BF_VERTEX_COORDS_END"
}
puts "BF_HARNESS_COMPLETED=1"
