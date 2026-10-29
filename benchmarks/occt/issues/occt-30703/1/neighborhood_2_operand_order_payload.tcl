# Derived neighbor: swap the two original surface operands in the official intersection command.
# Exact official fixture bytes and the original count/length oracle are retained.
foreach v4_visual {smallview donly fit checkview clpoles clknots} {
  set v4_saved_visual v4_original_$v4_visual
  if {[llength [info commands $v4_visual]] > 0 && [llength [info commands $v4_saved_visual]] == 0} {
    rename $v4_visual $v4_saved_visual
  }
  if {[llength [info commands $v4_visual]] == 0} {proc $v4_visual {args} {}}
}
proc Error: {args} { puts "M30703_OFFICIAL_COUNT_FAILURE [join $args { }]" }
restore [locate_data_file bug30703s1] s1
restore [locate_data_file bug30703s2] s2
puts "M30703_TYPES_s1=[whatis s1]"
puts "M30703_TYPES_s2=[whatis s2]"
puts "M30703_OPERAND_ORDER=s2,s1"
set info [intersect res s2 s1]
puts "__BENCH_ASSERT_PASS__ operand_order"
set v4_count [llength $info]
puts "M30703_INFO_COUNT=$v4_count expected=1"
if {$v4_count == 1} { puts "__BENCH_ASSERT_PASS__ solution_count" } else { puts "__BENCH_ASSERT_FAIL__ solution_count observed=$v4_count expected=1" }
checklength res -l 22.9782037
if {[info exists ::res]} {
  set v4_len_report [length res 1.0e-4]
  if {[regexp {The +length +res +is +([-0-9.+eE]+)} $v4_len_report -> v4_length]} {
    set v4_expected 22.9782037
    set v4_rel [expr {abs($v4_length-$v4_expected)/$v4_expected}]
    puts "M30703_LENGTH_OBSERVED=$v4_length expected=$v4_expected relative_error=$v4_rel official_relative_limit=0.01"
    if {$v4_length > 0.0 && $v4_rel <= 0.01} { puts "__BENCH_ASSERT_PASS__ curve_length" } else { puts "__BENCH_ASSERT_FAIL__ curve_length observed=$v4_length expected=$v4_expected relative_error=$v4_rel" }
  } else { puts "M30703_LENGTH_REPORT_UNPARSED=$v4_len_report"; puts "__BENCH_ASSERT_FAIL__ curve_length no_numeric_length" }
} else { puts "M30703_LENGTH_NOT_MEASURED=no_res_object" }
