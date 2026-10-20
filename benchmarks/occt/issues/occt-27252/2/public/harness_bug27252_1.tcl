# BF_CASE_ID: M27252_original
set bf_case_dir [file dirname [file normalize [info script]]]
set imagedir [file join $bf_case_dir images]; file mkdir $imagedir
set test_image {M27252_original}
set bf_data_dir [file join $bf_case_dir inputs]
proc locate_data_file {name} {
  if {![regexp {^[A-Za-z0-9_.-]+$} $name]} { error "unlocked data name" }
  set path [file join $::bf_data_dir $name]
  if {![file isfile $path]} { error "locked input missing: $name" }
  return $path
}
source [file join $bf_case_dir draw_pure_display_noop.tcl]
puts "BF_HARNESS_CASE=M27252_original"
pload TOPTEST
puts "BF_TOPTEST_LOADED=1"
set bf_source_rc [catch {source [file join $bf_case_dir bug27252_1.tcl]} bf_source_message bf_source_options]
puts "BF_TEST_SOURCE_RETURNED=1"
puts "BF_SOURCE_RC=$bf_source_rc"
if {$bf_source_rc != 0} {
  puts "BF_SOURCE_ERROR=$bf_source_message"
  if {[dict exists $bf_source_options -errorinfo]} { puts "BF_SOURCE_ERRORINFO=[dict get $bf_source_options -errorinfo]" }
}
foreach var {Toler NbCurv GoodNbCurv MaxTol log} { if {[info exists $var]} { puts "BF_VAR_$var=[set $var]" } }
if {[info exists log]} { puts "BF_OFFICIAL_BOP_LOG_BEGIN"; puts $log; puts "BF_OFFICIAL_BOP_LOG_END" }
puts "BF_HARNESS_COMPLETED=1"
