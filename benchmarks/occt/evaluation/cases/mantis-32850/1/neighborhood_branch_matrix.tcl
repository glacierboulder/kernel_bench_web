set here [file dirname [file normalize [info script]]]
set helper [file join $here neighbor_support.tcl]
if {![file isfile $helper]} {
  set helper [file join [file dirname [file dirname $here]] mantis-30082 5 neighbor_support.tcl]
}
source $helper

pload MODELING

proc mn_check_m32850_branch_matrix {scale angle dx dy dz suffix} {
  set s1 cylinder_surface1_$suffix
  set s2 cylinder_surface2_$suffix
  set f1 cylinder_face1_$suffix
  set f2 cylinder_face2_$suffix

  uplevel #0 [list cylinder $s1 25.8071575178163 0 -373.974517822281 \
    0 1 0 -1.73024882663956e-06 0 0.999999999998503 408.974517822893]
  uplevel #0 [list trim $s1 $s1 0 0.0225015452057227 -146.010003766057 2146.01000376606]
  uplevel #0 [list cylinder $s2 0 1974.19284248218 -373.974517822281 \
    1 0 0 0 1.73024882663956e-06 0.999999999998503 408.974517822893]
  uplevel #0 [list trim $s2 $s2 0 0.0225015452057227 -146.010003766057 946.010003766057]
  uplevel #0 [list mkface $f1 $s1]
  uplevel #0 [list mkface $f2 $s2]

  foreach face [list $f1 $f2] {
    uplevel #0 [list tscale $face 0 0 0 $scale]
    uplevel #0 [list trotate $face 0 0 0 1 2 3 $angle]
    uplevel #0 [list ttranslate $face $dx $dy $dz]
  }
  set sf1 support1_$suffix
  set sf2 support2_$suffix
  uplevel #0 [list mksurface $sf1 $f1]
  uplevel #0 [list mksurface $sf2 $f2]

  set report [uplevel #0 [list bopcurves $f1 $f2]]
  set count [mn_report_intersection $report 4 "M32850 scale=$scale pose=$suffix forward order"]
  if {$count != 4} { return }
  set tolerance_ceiling [expr {1.0e-12*max(1.0,$scale)}]
  bench_assert_range $::mn_last_reported_tolerance 0.0 $tolerance_ceiling \
    "M32850 $suffix reported tolerance remains at the near-orthogonal case scale"
  set root branch_$suffix
  mn_retain_curves c $root $count

  set lengths {}
  for {set i 1} {$i <= $count} {incr i} {
    set curve ${root}_$i
    set curve_length [mn_curve_length $curve]
    bench_assert_range $curve_length 1.0e-7 1.0e100 "M32850 $suffix branch $i has finite positive length"
    lappend lengths [expr {$curve_length/$scale}]
    foreach surface [list $sf1 $sf2] {
      set cylinder first
      if {$surface eq $sf2} { set cylinder second }
      set maximum [mn_m32850_cylinder_residual_max $curve $cylinder $scale $angle $dx $dy $dz 201 \
        "$suffix branch$i $cylinder analytic cylinder"]
      bench_assert_range $maximum 0.0 [expr {2.0e-9*max(1.0,$scale)}] \
        "M32850 $suffix branch $i independently sampled analytic residual on $cylinder cylinder"
    }
  }
  puts "MN_M32850_NORMALIZED_LENGTHS suffix=$suffix scale=$scale sorted=[lsort -real $lengths]"
  # A count can be forged by returning the same curve repeatedly. The sampled
  # symmetric Hausdorff checks require four geometrically distinct branches.
  for {set i 1} {$i <= $count} {incr i} {
    for {set j [expr {$i+1}]} {$j <= $count} {incr j} {
      set distance [mn_curve_sample_hausdorff ${root}_$i ${root}_$j 41]
      puts "MN_M32850_BRANCH_PAIR suffix=$suffix branch_a=$i branch_b=$j samples=41 symmetric_max_nearest_distance=$distance"
      bench_assert_range $distance [expr {1.0e-4*max(1.0,$scale)}] 1.0e100 \
        "M32850 $suffix branch $i and $j occupy distinct sampled loci"
    }
  }
  set lengths [lsort -real $lengths]
  bench_assert {[llength $lengths] == 4} "$suffix normalized branch list has four entries"
  for {set i 0} {$i < 3} {incr i} {
    bench_assert_range [lindex $lengths $i] 0.0009 0.0011 \
      "M32850 $suffix expected short branch [expr {$i+1}] length coverage"
  }
  bench_assert_range [lindex $lengths 3] 12.9 13.1 \
    "M32850 $suffix expected long branch length coverage"

  # Reversing the input order should preserve the same four physical branches.
  set reverse_report [uplevel #0 [list bopcurves $f2 $f1]]
  set reverse_count [mn_report_intersection $reverse_report 4 "M32850 scale=$scale pose=$suffix reverse order"]
  if {$reverse_count != 4} { return }
  set reverse_root reverse_branch_$suffix
  mn_retain_curves c $reverse_root $reverse_count
  set reverse_lengths {}
  for {set i 1} {$i <= $reverse_count} {incr i} {
    set reverse_curve ${reverse_root}_$i
    set length [mn_curve_length $reverse_curve]
    lappend reverse_lengths [expr {$length/$scale}]
    foreach surface [list $sf1 $sf2] {
      set cylinder first
      if {$surface eq $sf2} { set cylinder second }
      set maximum [mn_m32850_cylinder_residual_max $reverse_curve $cylinder $scale $angle $dx $dy $dz 201 \
        "$suffix reverse branch$i $cylinder analytic cylinder"]
      bench_assert_range $maximum 0.0 [expr {2.0e-9*max(1.0,$scale)}] \
        "M32850 $suffix reverse branch $i independently sampled analytic residual on $cylinder cylinder"
    }
  }
  for {set i 1} {$i <= $reverse_count} {incr i} {
    for {set j [expr {$i+1}]} {$j <= $reverse_count} {incr j} {
      set distance [mn_curve_sample_hausdorff ${reverse_root}_$i ${reverse_root}_$j 41]
      puts "MN_M32850_REVERSE_BRANCH_PAIR suffix=$suffix branch_a=$i branch_b=$j samples=41 symmetric_max_nearest_distance=$distance"
      bench_assert_range $distance [expr {1.0e-4*max(1.0,$scale)}] 1.0e100 \
        "M32850 $suffix reverse branch $i and $j occupy distinct sampled loci"
    }
  }
  set reverse_lengths [lsort -real $reverse_lengths]
  for {set i 0} {$i < 3} {incr i} {
    bench_assert_range [lindex $reverse_lengths $i] 0.0009 0.0011 \
      "M32850 $suffix reversed expected short branch [expr {$i+1}] length coverage"
  }
  bench_assert_range [lindex $reverse_lengths 3] 12.9 13.1 \
    "M32850 $suffix reversed expected long branch length coverage"
  for {set i 0} {$i < [llength $lengths]} {incr i} {
    bench_assert_close [lindex $reverse_lengths $i] [lindex $lengths $i] 0.05 \
      "M32850 $suffix operand-order branch [expr {$i+1}] length invariant"
  }
}

# Multiple physical scales and world poses probe the same near-orthogonal
# trimmed-cylinder branches, with dense surface-distance sampling and order swap.
mn_check_m32850_branch_matrix 0.5 29 80 -45 18 half_scale_rotated
mn_check_m32850_branch_matrix 2.0 83 -150 60 27 double_scale_rotated

bench_finish
