pload TOPTEST
psphere sph 2
box bx 10 10 10 2 2 2
bfuse result sph bx
checkshape result
checkprops result -s 74.265482457 -v 41.510321638
puts "__BENCH_ASSERT_PASS__ disjoint_solid_union area_volume"
puts "BENCH_ASSERT_PASS disjoint_solid_union \"upstream geometry assertions completed\" kind=expression"
puts "__BENCH_ORACLE_COMPLETE__"
puts "BENCH_ORACLE_OK assertions=1 numeric_assertions=0"
puts "TEST_DONE assertions=1 numeric_assertions=0"
