namespace eval ::single20 {
    variable count 0
    variable numeric_count 0
}

proc ::single20::finite {value} {
    return [expr {[string is double -strict $value] && ![catch {expr {abs(double($value)) <= 1.7976931348623157e308}} result] && $result}]
}

proc ::single20::assert {id passed detail {kind expression}} {
    variable count
    variable numeric_count
    incr count
    if {$kind eq "numeric"} {incr numeric_count}
    set detail [string map [list "\n" "|" "\r" ""] $detail]
    set state [expr {$passed ? "PASS" : "FAIL"}]
    puts "BENCH_ASSERT_${state} $id $detail kind=$kind"
}

proc ::single20::finish {} {
    variable count
    variable numeric_count
    if {$count == 0} {error "no geometric assertions executed"}
    puts {__BENCH_ORACLE_COMPLETE__}
    puts "BENCH_ORACLE_OK assertions=$count numeric_assertions=$numeric_count"
    puts "TEST_DONE assertions=$count numeric_assertions=$numeric_count"
}
