# Healthy analytic control for the same Geom surface-surface intersection entry point.
cylinder c 0 0 0 0 0 1 5
plane p 0 0 0 0 0 1
set curves [intersect regcurve p c]
set v4_n [llength $curves]
puts "M29972_REG_CURVES=$v4_n expected=1"
if {$v4_n == 1} { puts "__BENCH_ASSERT_PASS__ solution_count" } else { puts "__BENCH_ASSERT_FAIL__ solution_count observed=$v4_n expected=1" }
checklength regcurve -l 31.41592653589793
set v4_len_report [length regcurve 1.0e-4]
if {[regexp {The +length +regcurve +is +([-0-9.+eE]+)} $v4_len_report -> v4_len]} {
  set v4_rel [expr {abs($v4_len-31.41592653589793)/31.41592653589793}]
  puts "M29972_REG_LENGTH=$v4_len expected=31.41592653589793 relative_error=$v4_rel"
  if {$v4_len > 0 && $v4_rel <= 0.01} { puts "__BENCH_ASSERT_PASS__ curve_length" } else { puts "__BENCH_ASSERT_FAIL__ curve_length observed=$v4_len expected=31.41592653589793" }
} else { puts "__BENCH_ASSERT_FAIL__ curve_length no_numeric_length" }
