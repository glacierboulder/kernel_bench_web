# BF_CASE_ID: M27780_original
set bf_case_dir [file dirname [file normalize [info script]]]
set imagedir [file join $bf_case_dir images]; file mkdir $imagedir
set test_image {M27780_original}
proc locate_data_file {name} {
  if {![regexp {^[A-Za-z0-9_.-]+$} $name]} { error "unlocked data name" }
  set path [file join $::bf_case_dir inputs $name]
  if {![file isfile $path]} { error "locked input missing: $name" }
  return $path
}
source [file join $bf_case_dir draw_pure_display_noop.tcl]
pload TOPTEST
puts "BF_HARNESS_CASE=M27780_original"
set bf_required_commands {restore explode bopcurves pcurve trim 2dcvalue dset dval view don 2dfit checkview}
set bf_missing_commands {}
foreach cmd $bf_required_commands { if {[llength [info commands $cmd]] == 0} { lappend bf_missing_commands $cmd } }
puts "BF_REQUIRED_COMMANDS_MISSING=$bf_missing_commands"
set bf_source_rc [catch {source [file join $bf_case_dir bug27780.tcl]} bf_source_result bf_source_options]
puts "BF_TEST_SOURCE_RETURNED=1"
puts "BF_SOURCE_RC=$bf_source_rc"
if {$bf_source_rc != 0} {
  puts "BF_SOURCE_ERROR=$bf_source_result"
  if {[dict exists $bf_source_options -errorinfo]} { puts "BF_SOURCE_ERRORINFO=[dict get $bf_source_options -errorinfo]" }
}
if {[info exists dot]} { catch { puts "BF_VAR_dot=[dval dot]" } }
puts "BF_HARNESS_COMPLETED=1"
