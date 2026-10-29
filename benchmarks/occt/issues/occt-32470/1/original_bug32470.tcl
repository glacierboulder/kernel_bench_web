pload TOPTEST
source [file join [file dirname [info script]] official_bug32470.tcl]
puts "BENCH_ASSERT_PASS official_oracle_completed \"upstream geometry assertions completed\" kind=expression"
puts "__BENCH_ORACLE_COMPLETE__"
puts "BENCH_ORACLE_OK assertions=1 numeric_assertions=0"
puts "TEST_DONE assertions=1 numeric_assertions=0"
