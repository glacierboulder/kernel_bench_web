source [file join [file dirname [info script]] bootstrap.tcl]
pcone cone 10 0 20
box clip -20 -20 5 40 40 10
bcommon result cone clip
checkshape result
set bc [bopcheck result]
stage3_assert [regexp {This shape seems to be OK} $bc] bop_valid "bopcheck=$bc"
checkprops result -v 850.8480103472357
set ptxt [vprops result 1.e-7]
if {![regexp {Mass\s*:\s*([-0-9.+eE]+)} $ptxt all mass]} {stage3_assert 0 analytic_volume "vprops=$ptxt"} else {
  set observed [expr {double($mass)}]
  set expected 850.8480103472357
  set ok [expr {abs($observed-$expected) <= 0.01*$expected}]
  stage3_assert $ok analytic_volume "expected=$expected observed=$observed"
}

v4_finish
