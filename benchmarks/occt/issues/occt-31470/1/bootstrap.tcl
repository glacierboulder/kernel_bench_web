# Private v4 DRAW setup; suite routing is hash-locked by dispatch_lock.json.
set ::v4_assertions 0
set ::v4_numeric_assertions 0
pload TOPTEST
set ::v4_casroot $::env(CASROOT)
foreach ::v4_name {StandardCommands.tcl TestCommands.tcl CheckCommands.tcl} {
  source [file join $::v4_casroot src DrawResources $::v4_name]
}
source [file join $::v4_casroot tests bugs modalg_7 begin]
set imagedir [file dirname [info script]]
set test_image v4_geometry
foreach ::v4_visual {checkview v2d} {if {[llength [info commands $::v4_visual]] > 0} {rename $::v4_visual v4_original_$::v4_visual}}
proc checkview {args} {puts {V4_VISUALIZATION_ONLY_SKIPPED}}
proc v2d {args} {puts {V4_VISUALIZATION_ONLY_SKIPPED}}
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
