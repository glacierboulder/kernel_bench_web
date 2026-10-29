# Healthy inline control: the plane z=0 intersects the radius-5 z-axis cylinder
# in one exact circle, whose length is 2*pi*5. This uses the same IntPatch
# surface-surface `intersect` entry point as the original case.
foreach v4_visual {smallview donly fit checkview clpoles clknots} {
  set v4_saved_visual v4_original_$v4_visual
  if {[llength [info commands $v4_visual]] > 0 && [llength [info commands $v4_saved_visual]] == 0} {
    rename $v4_visual $v4_saved_visual
  }
  if {[llength [info commands $v4_visual]] == 0} {proc $v4_visual {args} {}}
}
proc Error: {args} { puts "M30703_REG_COUNT_FAILURE [join $args { }]" }
cylinder c 0 0 0 0 0 1 5
plane p 0 0 0 0 0 1
puts "M30703_REG_TYPES_c=[whatis c]"
puts "M30703_REG_TYPES_p=[whatis p]"
set info [intersect res c p]
set v4_count [llength $info]
puts "M30703_REG_INFO_COUNT=$v4_count expected=1"
if {$v4_count == 1} { puts "__BENCH_ASSERT_PASS__ solution_count" } else { puts "__BENCH_ASSERT_FAIL__ solution_count observed=$v4_count expected=1" }
checklength res -l 31.41592653589793
if {[info exists ::res]} {
  set v4_len_report [length res 1.0e-4]
  if {[regexp {The +length +res +is +([-0-9.+eE]+)} $v4_len_report -> v4_length]} {
    set v4_expected 31.41592653589793
    set v4_rel [expr {abs($v4_length-$v4_expected)/$v4_expected}]
    puts "M30703_REG_LENGTH_OBSERVED=$v4_length expected=$v4_expected relative_error=$v4_rel official_relative_limit=0.01"
    if {$v4_length > 0.0 && $v4_rel <= 0.01} { puts "__BENCH_ASSERT_PASS__ curve_length" } else { puts "__BENCH_ASSERT_FAIL__ curve_length observed=$v4_length expected=$v4_expected relative_error=$v4_rel" }
  } else { puts "M30703_REG_LENGTH_REPORT_UNPARSED=$v4_len_report"; puts "__BENCH_ASSERT_FAIL__ curve_length no_numeric_length" }
} else { puts "M30703_REG_LENGTH_NOT_MEASURED=no_res_object" }
