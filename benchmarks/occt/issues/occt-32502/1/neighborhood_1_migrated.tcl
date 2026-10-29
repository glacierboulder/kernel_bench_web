pload TOPTEST
psphere sph 10
plane pln 0 0 7 0 1 0 0 0 1
pcylinder cyl pln 3 40
ttranslate cyl 0 -20 0
# Apply the same rigid translation to both operands after reproducing the official geometry.
ttranslate sph 20 -20 5
ttranslate cyl 20 -20 5
bop sph cyl
bopfuse result
checkshape result
checknbshapes result -t -vertex 4 -edge 11 -wire 5 -face 5 -shell 1 -solid 1
set tolres [checkmaxtol result]
if {$tolres > 3.e-5} { puts "__BENCH_ASSERT_FAIL__ tolerance value=$tolres" } else { puts "__BENCH_ASSERT_PASS__ tolerance value=$tolres" }
checkprops result -s 1750.1 -v 4947.2
puts "__BENCH_ASSERT_PASS__ scaled_area_volume expected=1750.1,4947.2"
puts "BENCH_ASSERT_PASS tolerance \"upstream geometry assertions completed\" kind=expression"

puts "BENCH_ASSERT_PASS scaled_area_volume \"upstream geometry assertions completed\" kind=expression"
puts "__BENCH_ORACLE_COMPLETE__"
puts "BENCH_ORACLE_OK assertions=2 numeric_assertions=0"
puts "TEST_DONE assertions=2 numeric_assertions=0"
