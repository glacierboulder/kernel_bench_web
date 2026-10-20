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
  set tempRoot [pwd]
  if {[info exists ::env(TMPDIR)] && $::env(TMPDIR) ne ""} {set tempRoot $::env(TMPDIR)}
  set path [file join $tempRoot [format ".occt_%s_%d.brep" $key [pid]]]
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

set ::fixture_bug31602_brep {REJSZXBfRHJhd2FibGVTaGFwZQoKQ0FTQ0FERSBUb3BvbG9neSBWMSwgKGMpIE1hdHJhLURhdGF2aXNpb24KTG9jYXRpb25zIDAKQ3VydmUyZHMgOQoxIDAgNTUuOTAxNjk5NDM3NTAwMTYzIDEgMCAKMSAwIDAgMSAwIAoxIDYuMjgzMTg1MzA3MTc5NTg2MiAwIDAgMSAKMSA0LjEzODkxMTQzNTgwMjU4MzZlLTEzIDAgMCAxIAoxIDAgMzAwIDEgMCAKMSA2LjI4MzE4NTMwNzE3OTU4NjIgMCAtMSAwIAoxIC00LjEzODkxMTQzNTgwMjU4MzZlLTEzIDAgLTAgLTEgCjEgNi4yODMxODUzMDcxNzk1ODYyIDAgLTAgLTEgCjEgNi4yODMxODUzMDcxNzk1ODYyIC03MDggLTEgMCAKQ3VydmVzIDYKMiA4LjI0NTAxMzY1NTc0Njk5OThlLTA3IDU3Ni40NTE3NTEyMjU0MzAwMyAxMjIuNjgwNzgyNTA4MDkgMS44Nzc2NTU4NjgyMDQyMjg5ZS0wOCAwLjg5MTAwNjUyNDE4ODEwODU1IDAuNDUzOTkwNDk5NzQwMDU1MzQgMC45OTk5OTk5OTk5OTk5OTk4OSAtMi4xMDczNDAwNjQzODExNTEzZS0wOCAtNC42NzQ0NTM4MzgyMDI3NDI4ZS0xNCA5LjU2NzA4MjAzOTgxNzcyNTRlLTA5IDAuNDUzOTkwNDk5NzQwMDU1MjkgLTAuODkxMDA2NTI0MTg4MTA4ODggMjAwCjEgMjAwLjAwMDAwMDgyNDUwMDAxIDU3Ni40NTE3NDcwMTA3NDk5NSAxMjIuNjgwNzgyNTA4MDggMS44Nzc2NTU4Nzc2NzgyMjg5ZS0wOCAwLjg5MTAwNjUyNDE4ODEwODU1IDAuNDUzOTkwNDk5NzQwMDU1MzQgCjIgNi40NTc0Njg5NzAxODgwMDAxZS0wNiA4NDMuNzUzNzA4NDgxOTM5OTUgMjU4Ljg3NzkzMjQyOTk1MDAyIDEuODc3NjU1ODY4MjA0MjI4OWUtMDggMC44OTEwMDY1MjQxODgxMDg1NSAwLjQ1Mzk5MDQ5OTc0MDA1NTM0IDAuOTk5OTk5OTk5OTk5OTk5ODkgLTIuMTA3MzQwMDY0MzgxMTUxM2UtMDggLTQuNjc0NDUzODM4MjAyNzQyOGUtMTQgOS41NjcwODIwMzk4MTc3MjU0ZS0wOSAwLjQ1Mzk5MDQ5OTc0MDA1NTI5IC0wLjg5MTAwNjUyNDE4ODEwODg4IDIwMAoyIDAgMCAtMTUwIDAgMCAxIDEgMCAtMCAtMCAxIDAgNzUwCjEgNzUwIDAgLTE1MCAwIDAgMSAKMiAwIDAgNTU4IDAgMCAxIDEgMCAtMCAtMCAxIDAgNzUwClBvbHlnb24zRCAwClBvbHlnb25PblRyaWFuZ3VsYXRpb25zIDAKU3VyZmFjZXMgNgoyIDguMjQ1MDEzNjU1NzQ2OTk5OGUtMDcgNTc2LjQ1MTc1MTIyNTQzMDAzIDEyMi42ODA3ODI1MDgwOSAxLjg3NzY1NTg2ODIwNDIyODllLTA4IDAuODkxMDA2NTI0MTg4MTA4NTUgMC40NTM5OTA0OTk3NDAwNTUzNCAwLjk5OTk5OTk5OTk5OTk5OTg5IC0yLjEwNzM0MDA2NDM4MTE1MTNlLTA4IC00LjY3NDQ1MzgzODIwMjc0MjhlLTE0IDkuNTY3MDgyMDM5ODE3NzI1NGUtMDkgMC40NTM5OTA0OTk3NDAwNTUyOSAtMC44OTEwMDY1MjQxODgxMDg4OCAyMDAKMyAtMS4xNDMyNjU2ODUyNzVlLTA3IDUzMS45MDE0MjUwMTYwMDk5NyA5OS45ODEyNTc1MjExMTkwMDUgMS44Nzc2NTU4NjgyMDQyMjg5ZS0wOCAwLjg5MTAwNjUyNDE4ODEwODU1IDAuNDUzOTkwNDk5NzQwMDU1MzQgMC45OTk5OTk5OTk5OTk5OTk4OSAtMi4xMDczNDAwNjQzODExNTEzZS0wOCAtNC42NzQ0NTM4MzgyMDI3NDI4ZS0xNCA5LjU2NzA4MjAzOTgxNzcyNTRlLTA5IDAuNDUzOTkwNDk5NzQwMDU1MjkgLTAuODkxMDA2NTI0MTg4MTA4ODggMTc1CjAuNDYzNjQ3NjA5MDAwOTk5OTkKMSA2LjQ1NzQ2ODk3MDE4ODAwMDFlLTA2IDg0My43NTM3MDg0ODE5Mzk5NSAyNTguODc3OTMyNDI5OTUwMDIgMS44Nzc2NTU4NjgyMDQyMjg5ZS0wOCAwLjg5MTAwNjUyNDE4ODEwODU1IDAuNDUzOTkwNDk5NzQwMDU1MzQgMC45OTk5OTk5OTk5OTk5OTk4OSAtMi4xMDczNDAwNjQzODExNTEzZS0wOCAtNC42NzQ0NTM4MzgyMDI3NDI4ZS0xNCA5LjU2NzA4MjAzOTgxNzcyNTRlLTA5IDAuNDUzOTkwNDk5NzQwMDU1MjkgLTAuODkxMDA2NTI0MTg4MTA4ODggCjIgMCAwIC0xNTAgLTAgLTAgLTEgMSAwIC0wIDAgLTEgMCA3NTAKMSAwIDAgLTE1MCAwIDAgMSAxIDAgLTAgLTAgMSAwIAoxIDAgMCA1NTggMCAwIDEgMSAwIC0wIC0wIDEgMCAKVHJpYW5ndWxhdGlvbnMgMAoKVFNoYXBlcyAxNQpWZQoxZS0wNwoyMDAuMDAwMDAwODI0NSA1NzYuNDUxNzQ3MDEwNzUgMTIyLjY4MDc4MjUwODA4CjAgMAoKMDEwMTEwMQoqCkVkCiAxZS0wNyAxIDEgMAoxICAxIDAgMCA2LjI4MzE4NTMwNzE3OTU5CjIgIDEgMiAwIDAgNi4yODMxODUzMDcxNzk1OQoyICAyIDEgMCAwIDYuMjgzMTg1MzA3MTc5NTkKNCBDMCAyIDAgMSAwCjAKCjAxMDEwMDAKKzE1IDAgLTE1IDAgKgpWZQoxZS0wNwoyMDAuMDAwMDA2NDU3NDYgODQzLjc1MzcwNDI2NzI2IDI1OC44Nzc5MzI0Mjk5NAowIDAKCjAxMDExMDEKKgpFZAogMWUtMDcgMSAxIDAKMSAgMiAwIDAgMjk5Ljk5OTk5OTk5OTk5OAozICAzIDRDTiAxIDAgMCAyOTkuOTk5OTk5OTk5OTk4CjAKCjAxMDEwMDAKKzE1IDAgLTEzIDAgKgpFZAogMWUtMDcgMSAxIDAKMSAgMyAwIDAgNi4yODMxODUzMDcxNzk1OQoyICA1IDEgMCAwIDYuMjgzMTg1MzA3MTc5NTkKNCBDMCAxIDAgMyAwCjAKCjAxMDEwMDAKKzEzIDAgLTEzIDAgKgpXaQoKMDEwMTEwMAorMTQgMCArMTIgMCAtMTEgMCAtMTIgMCAqCkZhCjAgIDFlLTA3IDEgMAoKMDExMTAwMAorMTAgMCAqClZlCjFlLTA3Cjc1MCAwIC0xNTAKMCAwCgowMTAxMTAxCioKRWQKIDFlLTA3IDEgMSAwCjEgIDQgMCAwIDYuMjgzMTg1MzA3MTc5NTkKMiAgNiA0IDAgMCA2LjI4MzE4NTMwNzE3OTU5CjQgQzAgNCAwIDUgMAowCgowMTAxMDAwCis4IDAgLTggMCAqClZlCjFlLTA3Cjc1MCAwIDU1OAowIDAKCjAxMDExMDEKKgpFZAogMWUtMDcgMSAxIDAKMSAgNSAwIDAgNzA4CjMgIDcgOENOIDQgMCAwIDcwOAowCgowMTAxMDAwCis4IDAgLTYgMCAqCkVkCiAxZS0wNyAxIDEgMAoxICA2IDAgMCA2LjI4MzE4NTMwNzE3OTU5CjIgIDkgNCAwIDAgNi4yODMxODUzMDcxNzk1OQo0IEMwIDQgMCA2IDAKMAoKMDEwMTAwMAorNiAwIC02IDAgKgpXaQoKMDEwMTEwMAorNyAwICs1IDAgLTQgMCAtNSAwICoKRmEKMCAgMWUtMDcgNCAwCgowMTExMDAwCiszIDAgKgpDbwoKMTEwMDAwMAorOSAwICsyIDAgKgoKKzEgMCAKMAoK}

pload MODELING
bench_restore_b64 $::fixture_bug31602_brep f M31602
explode f f
set log [bopcurves f_1 f_2 -2d]
if {![regexp {Tolerance Reached=+([-0-9.+eE]+)\n+([-0-9.+eE]+)} $log full tol n]} {error "unparseable bopcurves result: $log"}
bench_assert_range $tol 0 2.5e-6 "intersection tolerance bound"
bench_assert {$n == 1} "one intersection branch"
bench_assert_close [bench_length c_1] 1340.6982492258749 0.02 "3D intersection length"
bench_assert_close [bench_length c2d1_1] 407.78567590999006 0.02 "first pcurve length"
bench_assert_close [bench_length c2d2_1] 897.8658894846285 0.02 "second pcurve length"
mksurface s1 f_1; mksurface s2 f_2
bounds c_1 u0 u1
xdistcs c_1 s1 u0 u1 20 3.0e-6
xdistcs c_1 s2 u0 u1 20 3.0e-6
bench_finish
