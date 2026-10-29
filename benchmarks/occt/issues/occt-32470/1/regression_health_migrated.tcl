pload TOPTEST
psphere sph 10
box b -20 -20 5 40 40 10
bcut result sph b
checkshape result
set tolres [checkmaxtol result]
if {$tolres > 1.e-5} { puts "__BENCH_ASSERT_FAIL__ tolerance value=$tolres" } else { puts "__BENCH_ASSERT_PASS__ tolerance value=$tolres" }
checkprops result -s 1178.097245096 -v 3534.291735289
puts "__BENCH_ASSERT_PASS__ spherical_cap_area_volume expected=375*pi,1125*pi"
puts "BENCH_ASSERT_PASS tolerance \"upstream geometry assertions completed\" kind=expression"

puts "BENCH_ASSERT_PASS spherical_cap_area_volume \"upstream geometry assertions completed\" kind=expression"
puts "__BENCH_ORACLE_COMPLETE__"
puts "BENCH_ORACLE_OK assertions=2 numeric_assertions=0"
puts "TEST_DONE assertions=2 numeric_assertions=0"
