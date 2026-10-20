# Bundle-local gate around the unchanged official test or calibrated hidden oracle.
set bf_case_dir [file dirname [file normalize [info script]]];
set bf_bundle_root [file normalize [file join $bf_case_dir .. .. .. ..]]
set bf_asset_dir {}

set imagedir [file join $bf_case_dir images]; file mkdir $imagedir
set test_image {M29807_i5002}
set bf_data_dir [file join $bf_case_dir inputs]
proc locate_data_file {name} {
  if {![regexp {^[A-Za-z0-9_.-]+$} $name]} { error "unlocked data name" }
  set path [file join $::bf_data_dir $name]
  if {![file isfile $path]} { error "locked input missing: $name" }
  return $path
}
pload TOPTEST
puts "BF_TOPTEST_LOADED=1"
source [file join $bf_case_dir draw_pure_display_noop.tcl]
puts "BF_DISPLAY_ADAPTER_LOADED=1"
set bf_required_commands {cone intersect whatis bounds dval xdistcs mkedge bclearobjects bcleartools baddobjects bfillds bbuild checksection checkmaxtol checknbshapes}
set bf_missing_commands {}
foreach cmd $bf_required_commands { if {[llength [info commands $cmd]] == 0} { lappend bf_missing_commands $cmd } }
puts "BF_REQUIRED_COMMANDS_MISSING=$bf_missing_commands"
set bf_required_helpers {}
set bf_missing_helpers {}
foreach helper $bf_required_helpers { if {[llength [info commands $helper]] == 0} { lappend bf_missing_helpers $helper } }
puts "BF_REQUIRED_HELPERS_MISSING=$bf_missing_helpers"
set bf_wrapper_error_count 0
set bf_wrapper_output {}
rename ::puts ::bf_native_puts
proc ::puts {args} {
  set message [lindex $args end]
  lappend ::bf_wrapper_output $message
  if {[regexp -nocase {^(Error\s*:|BF_ORACLE_EVAL_ERROR:|Call of function .+ failed|Unknown (variable|function|command)\b)} $message]} { incr ::bf_wrapper_error_count }
  return [uplevel 1 [linsert $args 0 ::bf_native_puts]]
}
set bf_tcl_rc [catch {
  if {[llength $bf_missing_commands] != 0} { error "required Draw commands missing" }
  if {[llength $bf_missing_helpers] != 0} { error "required Tcl helper commands missing" }
  source [file join $bf_case_dir bug29807_i5002.tcl]
} bf_tcl_message bf_tcl_options]
puts "BF_TEST_SOURCE_RETURNED=1"
puts "BF_SOURCE_RC=$bf_tcl_rc"
if {$bf_tcl_rc != 0} { puts "BF_SOURCE_ERROR=$bf_tcl_message" }
puts "BF_WRAPPER_ERROR_COUNT=$bf_wrapper_error_count"
foreach var {ic Toler NbCurv bf_curve_count bf_point_count bf_root_checks bf_expected_volume} { if {[info exists $var]} { puts "BF_VAR_$var=[set $var]" } }
set bf_case_ok [expr {$bf_tcl_rc == 0 && [llength $bf_missing_commands] == 0 && $bf_wrapper_error_count == 0}]
if {$bf_case_ok} { puts "BF_CASE_ORACLE=pass"; puts "TEST_DONE" } else { puts "BF_CASE_ORACLE=fail" }
