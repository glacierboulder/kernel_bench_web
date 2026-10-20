# BF_CASE_ID: M27780_regression_finite_plane
set bf_case_dir [file dirname [file normalize [info script]]]
set bf_bundle_root [file normalize [file join $bf_case_dir .. .. .. ..]]
set bf_asset_dir [file normalize [file join $bf_bundle_root evaluation cases evaluator_assets occt-bf-group-b2613378-27780-27252-21494-v1]]
if {![file isdirectory $bf_asset_dir]} { set bf_asset_dir [file normalize [file join $bf_case_dir .. .. .. .. .. .. evaluator_assets occt-bf-group-b2613378-27780-27252-21494-v1]] }
if {![file isdirectory $bf_asset_dir]} { set bf_asset_dir [file normalize [file join $bf_case_dir .. .. evaluator_assets occt-bf-group-b2613378-27780-27252-21494-v1]] }
puts "BF_HARNESS_CASE=M27780_regression_finite_plane"
set bf_source_rc [catch {source [file join $bf_asset_dir tests m27780_regression_body.tcl]} bf_source_message bf_source_options]
puts "BF_TEST_SOURCE_RETURNED=1"
puts "BF_SOURCE_RC=$bf_source_rc"
if {$bf_source_rc != 0} {
  puts "BF_SOURCE_ERROR=$bf_source_message"
  if {[dict exists $bf_source_options -errorinfo]} { puts "BF_SOURCE_ERRORINFO=[dict get $bf_source_options -errorinfo]" }
}
puts "BF_HARNESS_COMPLETED=1"
