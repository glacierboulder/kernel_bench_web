set v4_dir [file dirname [info script]]
source [file join $v4_dir bootstrap.tcl]
proc Error: {args} { puts "Error: [join $args { }]" }
source [file join $v4_dir official_upstream.tcl]
if {[info exists ::info]} {
  set v4_count [llength $::info]
  puts "M30703_ORIGINAL_CURVE_COUNT=$v4_count expected=1"
  stage3_assert [expr {$v4_count == 1}] solution_count "observed=$v4_count expected=1"
} else {
  stage3_assert 0 solution_count {not measured: official intersection returned no info list}
}
set v4_whatis_error {}
if {[catch {set v4_res_description [whatis res]} v4_whatis_error]} {set v4_res_description {}}
puts "M30703_RESULT_TYPE={$v4_res_description} whatis_error={$v4_whatis_error}"
if {[regexp -nocase {^res is a .*curve} [string trim $v4_res_description]] && ![catch {set v4_length_report [length res 1.0e-4]} v4_length_error]} {
  if {[regexp {The +length +res +is +([-0-9.+eE]+)} $v4_length_report -> v4_length]} {
    set v4_expected_length 22.9782037
    set v4_relative_error [expr {abs($v4_length-$v4_expected_length)/$v4_expected_length}]
    puts "M30703_ORIGINAL_LENGTH=$v4_length expected=$v4_expected_length relative_error=$v4_relative_error"
    stage3_assert [expr {$v4_length > 0.0 && $v4_relative_error <= 0.01}] curve_length "observed=$v4_length expected=$v4_expected_length relative_error=$v4_relative_error official_relative_limit=0.01"
  } else {
    stage3_assert 0 curve_length "not measured: length report={$v4_length_report}"
  }
} else {
  stage3_assert 0 curve_length "not measured: whatis={$v4_res_description}; whatis_error={$v4_whatis_error}; length_error=[expr {[info exists v4_length_error] ? $v4_length_error : {not a curve object}}]"
}
stage3_assert 1 official_oracle_completed {official test body and named geometric measurements completed}
v4_finish
