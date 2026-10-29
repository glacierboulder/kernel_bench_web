set v4_dir [file dirname [info script]]
source [file join $v4_dir bootstrap.tcl]
set ::v4_xdistcs_results {}
rename ::xdistcs ::v4_native_xdistcs
proc ::xdistcs {args} {
  set result [uplevel #0 [linsert $args 0 ::v4_native_xdistcs]]
  lappend ::v4_xdistcs_results [list [lindex $args 0] [lindex $args 1] $result [lindex $args end]]
  return $result
}
source [file join $v4_dir official_upstream.tcl]
set v4_total_samples 0
set v4_global_max 0.0
set v4_error_count 0
foreach v4_row $::v4_xdistcs_results {
  set v4_curve [lindex $v4_row 0]
  set v4_surface [lindex $v4_row 1]
  set v4_result [lindex $v4_row 2]
  set v4_tol [lindex $v4_row 3]
  set v4_matches [regexp -all -inline {D=([-0-9.+eE]+)} $v4_result]
  set v4_count [expr {[llength $v4_matches] / 2}]
  set v4_max 0.0
  for {set v4_i 1} {$v4_i < [llength $v4_matches]} {incr v4_i 2} {
    set v4_raw [lindex $v4_matches $v4_i]
    if {![string is double -strict $v4_raw]} {puts "M29972_DIAG_PARSE_ERROR curve=$v4_curve surface=$v4_surface value=$v4_raw"; continue}
    set v4_d [expr {double($v4_raw)}]
    if {$v4_d > $v4_max} {set v4_max $v4_d}
  }
  incr v4_total_samples $v4_count
  if {$v4_max > $v4_global_max} {set v4_global_max $v4_max}
  set v4_errors [regexp -all -inline {Error in [^\r\n]*} $v4_result]
  incr v4_error_count [llength $v4_errors]
  puts "M29972_DIAG_XDISTCS curve=$v4_curve surface=$v4_surface samples=$v4_count max_sample_distance=$v4_max tolerance=$v4_tol errors=[llength $v4_errors]"
  foreach v4_err $v4_errors {puts "M29972_DIAG_ERROR curve=$v4_curve surface=$v4_surface $v4_err"}
}
puts "M29972_DIAG_SUMMARY calls=[llength $::v4_xdistcs_results] total_sample_distances=$v4_total_samples max_sample_distance=$v4_global_max official_tolerance=2.0e-7 error_count=$v4_error_count"
