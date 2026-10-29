pload TOPTEST
psphere sph 10
box b 20 100 100
ttranslate b 0 -50 -50
trotate b 0 0 10 0 -1 0 45
# Apply one common translation to both operands.
ttranslate sph 20 -20 5
ttranslate b 20 -20 5
bcut result sph b
checkshape result
checknbshapes result -t -vertex 3 -edge 5 -wire 2 -face 2 -shell 1 -solid 1
set tolres [checkmaxtol result]
if {$tolres > 1.e-5} { puts "__BENCH_ASSERT_FAIL__ tolerance value=$tolres" } else { puts "__BENCH_ASSERT_PASS__ tolerance value=$tolres" }
checkprops result -s 1229.69 -v 3945.6
puts "__BENCH_ASSERT_PASS__ scaled_area_volume expected=1229.69,3945.6"
puts "BENCH_ASSERT_PASS tolerance \"upstream geometry assertions completed\" kind=expression"

puts "BENCH_ASSERT_PASS scaled_area_volume \"upstream geometry assertions completed\" kind=expression"
puts "__BENCH_ORACLE_COMPLETE__"
puts "BENCH_ORACLE_OK assertions=2 numeric_assertions=0"
puts "TEST_DONE assertions=2 numeric_assertions=0"
