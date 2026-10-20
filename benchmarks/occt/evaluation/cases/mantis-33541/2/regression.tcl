# Inline this helper into every DRAW case that is frozen as a checkpoint.
# Frozen evaluation copies the checkpoint case itself, not sibling helper files.
namespace eval ::bench {
  variable assertions 0
  variable numeric_assertions 0
  variable failures 0
}

proc ::bench::_record {kind passed label detail} {
  variable assertions
  variable numeric_assertions
  variable failures
  incr assertions
  if {$kind eq "numeric"} { incr numeric_assertions }
  if {$passed} {
    puts "BENCH_ASSERT_PASS kind=$kind label=[list $label] detail=[list $detail]"
  } else {
    incr failures
    puts stderr "BENCH_ASSERT_FAIL kind=$kind label=[list $label] detail=[list $detail]"
  }
  return [expr {$passed ? 1 : 0}]
}

proc bench_assert {expression label} {
  if {[catch {uplevel 1 [list expr $expression]} value]} {
    return [::bench::_record expression 0 $label "evaluation_error=$value"]
  }
  return [::bench::_record expression [expr {$value ? 1 : 0}] $label "value=$value"]
}

proc bench_assert_close {actual expected tolerance label} {
  foreach value [list $actual $expected $tolerance] {
    if {![string is double -strict $value] ||
        [catch {expr {abs(double($value)) <= 1.7976931348623157e308}} finite] ||
        !$finite} {
      return [::bench::_record numeric 0 $label \
        "actual=$actual expected=$expected tolerance=$tolerance non_finite_or_non_numeric"]
    }
  }
  if {[catch {expr {double($tolerance) >= 0.0}} valid_tolerance] || !$valid_tolerance} {
    return [::bench::_record numeric 0 $label \
      "actual=$actual expected=$expected tolerance=$tolerance invalid_tolerance"]
  }
  set error [expr {abs(double($actual) - double($expected))}]
  set passed [expr {$error <= double($tolerance)}]
  return [::bench::_record numeric $passed $label \
    "actual=$actual expected=$expected tolerance=$tolerance absolute_error=$error"]
}

proc bench_assert_range {actual lower upper label} {
  foreach value [list $actual $lower $upper] {
    if {![string is double -strict $value] ||
        [catch {expr {abs(double($value)) <= 1.7976931348623157e308}} finite] ||
        !$finite} {
      return [::bench::_record numeric 0 $label \
        "actual=$actual lower=$lower upper=$upper non_finite_or_non_numeric"]
    }
  }
  set passed [expr {double($lower) <= double($actual) && double($actual) <= double($upper)}]
  return [::bench::_record numeric $passed $label \
    "actual=$actual lower=$lower upper=$upper"]
}

proc bench_finish {} {
  variable ::bench::assertions
  variable ::bench::numeric_assertions
  variable ::bench::failures
  if {$assertions < 1} {
    return -code error "bench_finish requires at least one assertion"
  }
  if {$failures != 0} {
    puts stderr "BENCH_ORACLE_FAILED assertions=$assertions failures=$failures"
    return -code error "one or more benchmark assertions failed"
  }
  puts "BENCH_ORACLE_OK assertions=$assertions numeric_assertions=$numeric_assertions"
  puts "TEST_DONE assertions=$assertions numeric_assertions=$numeric_assertions"
}

proc bench_restore_b64 {encoded shape key} {
  global $shape
  set path [file join [pwd] [format ".occt_%s_%d.brep" $key [pid]]]
  set f [open $path wb]; fconfigure $f -translation binary -encoding binary
  puts -nonewline $f [binary decode base64 $encoded]; close $f
  restore $path $shape; file delete -force $path
}
proc bench_curve_count {root} {
  set n 0
  for {set i 1} {$i <= 128} {incr i} {
    global ${root}_$i
    if {[string first "3d curve" [whatis ${root}_$i]] < 0} {break}
    incr n
  }
  return $n
}
proc bench_volume {shape} {
  global $shape
  set report [vprops $shape]
  if {![regexp -nocase {Mass[[:space:]]*:[[:space:]]*([-+0-9.eE]+)} $report -> value]} {error "cannot parse vprops for $shape: $report"}
  return $value
}
proc bench_length {shape} {
  global $shape
  set report [length $shape]
  if {![regexp {is[[:space:]]+([-+0-9.eE]+)} $report -> value]} {error "cannot parse length for $shape: $report"}
  return $value
}
proc bench_valid {shape label} {
  global $shape
  set audit [bopcheck $shape]
  bench_assert {[regexp {OK} $audit]} "$label BOP validity"
  set report [checkshape $shape]
  bench_assert {[regexp -nocase {valid} $report]} "$label checkshape validity"
}



pload MODELING
pcylinder c 1 1; psphere s 1
ttranslate s 1 1 1
bcut r c s; bcommon i c s
bench_valid r "intersecting control cut"
bench_valid i "intersecting control Common"
bench_assert_close [bench_volume r] 2.8126 2.0e-4 "control Cut volume"
bench_assert_close [bench_volume i] 0.328988 2.0e-5 "control Common volume"
pcylinder c_out 1 1; psphere s_out 1
ttranslate s_out 4 0 0
bcut r_out c_out s_out
bench_valid r_out "disjoint control cut"
bench_assert_close [bench_volume r_out] 3.141592653589793 4.0e-6 "disjoint cylinder volume"
checknbshapes r_out -solid 1
bench_finish
