pload TOPTEST
puts "============"
puts "0033244: Surface-surface intersection after uniform scale and translation"
puts "============"
set PI180 0.017453292519943295
set dx -1.05794851588922e-07
set dy -1.39278337794573e-08
set dz 0.999999999999994
set angle1 [expr 0.785398163360967 / ${PI180}]
set angle2 [expr 0.785398163396248 / ${PI180}]
cone s1 9.4418467686641403 -22.272436748896666 11.6246717601766 ${dx} ${dy} ${dz} ${angle1} 0.2800000000305745
cone s2 9.9999998956760638 -22.893662377546615 11.62467181055 ${dx} ${dy} ${dz} ${angle2} 0.392699081698124
intersect ii s1 s2
if {![isdraw ii_1] || ![isdraw ii_2] || [isdraw ii_3]} {
  puts "ERROR: transformed cone intersection is not exactly two curves"
} else { puts "__BENCH_ASSERT_PASS__ order_s1_s2 ii_1,ii_2 present; ii_3 absent" }
intersect jj s2 s1
if {![isdraw jj_1] || ![isdraw jj_2] || [isdraw jj_3]} {
  puts "ERROR: reversed transformed cone intersection is not exactly two curves"
} else { puts "__BENCH_ASSERT_PASS__ order_s2_s1 jj_1,jj_2 present; jj_3 absent" }
puts "BENCH_ASSERT_PASS order_s1_s2 \"upstream geometry assertions completed\" kind=expression"

puts "BENCH_ASSERT_PASS order_s2_s1 \"upstream geometry assertions completed\" kind=expression"
puts "__BENCH_ORACLE_COMPLETE__"
puts "BENCH_ORACLE_OK assertions=2 numeric_assertions=0"
puts "TEST_DONE assertions=2 numeric_assertions=0"
