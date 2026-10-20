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
cylinder s1 25.8071575178163 0 -373.974517822281 0 1 0 -1.73024882663956e-06 0 0.999999999998503 408.974517822893
trim s1 s1 0 0.0225015452057227 -146.010003766057 2146.01000376606
cylinder s2 0 1974.19284248218 -373.974517822281 1 0 0 0 1.73024882663956e-06 0.999999999998503 408.974517822893
trim s2 s2 0 0.0225015452057227 -146.010003766057 946.010003766057
mkface f1 s1; mkface f2 s2
copy f1 f1m; copy f2 f2m
ttranslate f1m 37 -19 12; ttranslate f2m 37 -19 12
set log [bopcurves f1m f2m]
if {![regexp {Tolerance Reached=+([-0-9.+eE]+)\n+([-0-9.+eE]+)} $log full tol n]} {error "unparseable translated result: $log"}
bench_assert {$n == 4} "rigid translation retains four branches"
bench_assert_range $tol 0 1.0e-12 "translated tolerance remains bounded"
set checked_n $n
if {$checked_n > 4} {set checked_n 4}
for {set i 1} {$i <= $checked_n} {incr i} {
  set c "c_$i"
  bench_assert_range [bench_length $c] 1.0e-7 1000 "$c positive finite length"
}
bench_finish
