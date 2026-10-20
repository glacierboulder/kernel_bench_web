# BF_CASE_ID: M27773
set bf_case_dir [file dirname [file normalize [info script]]]
set bf_bundle_root {}
set bf_data_dir [file join $bf_case_dir inputs]
set imagedir [file join $bf_case_dir images]; file mkdir $imagedir
set test_image {M27773}
proc locate_data_file {name} {
  if {![regexp {^[A-Za-z0-9_.-]+$} $name]} { error "unlocked data name" }
  set path [file join $::bf_data_dir $name]
  if {![file isfile $path]} { error "locked input missing: $name" }
  return $path
}
source [file join $bf_case_dir draw_pure_display_noop.tcl]
puts "BF_HARNESS_CASE=M27773"
pload TOPTEST
puts "BF_TOPTEST_LOADED=1"
set bf_source_rc [catch {source [file join $bf_case_dir bug27773.tcl]} bf_source_message bf_source_options]
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
if {"M27773" eq "M27773"} {
  set bf_vertex_rc [catch {explode result v} bf_vertex_message]
  puts "BF_VERTEX_COORDS_BEGIN"
  if {$bf_vertex_rc == 0} { puts [getcoords result_1 result_2] }
  puts "BF_VERTEX_COORDS_END"
}
puts "BF_HARNESS_COMPLETED=1"
