set imagedir [file dirname [info script]]
set test_image no_image
proc Error: {args} { puts "Error: [join $args { }]" }
box a 0 0 0 10 10 10
box b 5 5 5 15 15 15
bcommon result a b
checkshape result
puts "__BENCH_ASSERT_PASS__ reg_shape_check"
checknbshapes result -vertex 8 -edge 12 -wire 6 -face 6 -shell 1 -solid 1
puts "__BENCH_ASSERT_PASS__ reg_topology"
checkprops result -s 150 -v 125
puts "__BENCH_ASSERT_PASS__ reg_area_volume"
set valid [bopcheck result]
if {![regexp {This shape seems to be OK} $valid]} {error "healthy analytic common failed bopcheck: $valid"}
puts "__BENCH_ASSERT_PASS__ reg_valid"
puts "M33615_REG observed_area=150 expected=150 observed_volume=125 expected=125"
