pload TOPTEST
set ::bench_assertions 0
set ::bench_failures 0
proc stage3_assert {ok id detail} {
  incr ::bench_assertions
  set safe_detail [string map [list "\n" "|" "\r" ""] $detail]
  if {$ok} { puts "BENCH_ASSERT_PASS $id $safe_detail kind=expression" } else { puts "BENCH_ASSERT_FAIL $id $safe_detail kind=expression"; incr ::bench_failures }
}
plane p1 0 0 0 0 0 1
plane p2 0 0 0 0 1 0
set curves [intersect ii p1 p2]
set curve_count [llength $curves]
stage3_assert [expr {$curve_count == 1}] single_curve_count "curve_count=$curve_count"
set curve_dump ""
if {$curve_count == 1} { set curve_dump [dump [lindex $curves 0]] }
stage3_assert [expr {$curve_count == 1 && [regexp {Line} $curve_dump]}] line_type "curve_dump=$curve_dump"

puts "__BENCH_ORACLE_COMPLETE__"
puts "BENCH_ORACLE_OK assertions=$::bench_assertions numeric_assertions=0"
puts "TEST_DONE assertions=$::bench_assertions numeric_assertions=0"
