set here [file dirname [file normalize [info script]]]
set helper [file join $here neighbor_support.tcl]
if {![file isfile $helper]} {
  set helper [file join [file dirname [file dirname $here]] mantis-30082 5 neighbor_support.tcl]
}
source $helper

pload MODELING

proc mn_check_m30202_empty_pair {scale angle dx dy dz order_label} {
  mn_load_fixture mantis-30202 2
  mn_restore_b64 $::fixture_bug30202_src_brep b1 "m30202_source_$order_label"
  mn_restore_b64 $::fixture_bug30202_tool_brep b2 "m30202_tool_$order_label"

  foreach shape {b1 b2} {
    uplevel #0 [list tscale $shape 0 0 0 $scale]
    uplevel #0 [list trotate $shape 0 0 0 1 2 3 $angle]
    uplevel #0 [list ttranslate $shape $dx $dy $dz]
    uplevel #0 [list explode $shape f]
  }

  if {$order_label eq "forward"} {
    set first b1_5
    set second b2_7
  } else {
    set first b2_7
    set second b1_5
  }
  set report [uplevel #0 [list bopcurves $first $second -2d]]
  set empty [regexp -nocase {no 3d curves[\r\n]+[[:space:]]*has no 3d points} $report]
  puts "MN_M30202_EMPTY_PAIR scale=$scale order=$order_label report=[list $report]"
  bench_assert {$empty} \
    "M30202 scale=$scale rotation=$angle translation=($dx,$dy,$dz) $order_label reports no 3D curve or point for the selected face pair"
}

# The issue oracle is an empty intersection for this specific trimmed face
# pair. Probe two model scales and arbitrary rigid poses, with both operand
# orders, without registering unrelated generated constructions.
mn_check_m30202_empty_pair 0.5 37 100 -30 12 forward
mn_check_m30202_empty_pair 0.5 37 100 -30 12 reverse
mn_check_m30202_empty_pair 1.5 71 -240 55 36 forward
mn_check_m30202_empty_pair 1.5 71 -240 55 36 reverse

bench_finish
