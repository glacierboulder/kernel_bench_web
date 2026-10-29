# Private v4 DRAW setup; files are resolved relative to this issue directory.
set ::v4_assertions 0
set ::v4_numeric_assertions 0
pload TOPTEST
set ::v4_casroot $::env(CASROOT)
foreach ::v4_name {StandardCommands.tcl TestCommands.tcl CheckCommands.tcl} {
  source [file join $::v4_casroot src DrawResources $::v4_name]
}
set imagedir [file dirname [info script]]
set test_image no_image
foreach ::v4_visual {checkview v2d smallview don donly disp fit axo clpoles clknots} {
  if {[llength [info commands $::v4_visual]] > 0} {rename $::v4_visual v4_original_$::v4_visual}
  proc $::v4_visual {args} { }
}
proc stage3_assert {ok id detail} {
  set safe_detail [string map [list "\n" "|" "\r" ""] $detail]
  if {$ok} {puts "BENCH_ASSERT_PASS $id $safe_detail kind=expression"} else {puts "BENCH_ASSERT_FAIL $id $safe_detail kind=expression"}
  incr ::v4_assertions
}
proc v4_finish {} {
  puts {__BENCH_ORACLE_COMPLETE__}
  puts "BENCH_ORACLE_OK assertions=$::v4_assertions numeric_assertions=$::v4_numeric_assertions"
  puts "TEST_DONE assertions=$::v4_assertions numeric_assertions=$::v4_numeric_assertions"
}
rename ::puts ::v4_raw_puts
proc ::puts {args} {
  if {[llength $args] == 1 && [regexp {^__BENCH_ASSERT_(PASS|FAIL)__[[:space:]]+([^[:space:]]+)(.*)$} [lindex $args 0] -> status id detail]} {
    set ok [expr {$status eq "PASS"}]
    stage3_assert $ok $id [string trim $detail]
    return
  }
  return [uplevel 1 [linsert $args 0 ::v4_raw_puts]]
}
