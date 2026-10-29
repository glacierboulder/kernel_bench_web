set imagedir [file dirname [info script]]
set test_image no_image
proc Error: {args} { puts "Error: [join $args { }]" }
plane plane -5 0 4 -1 0 0
pcone cone plane 3 1 10
pcylinder cylinder 10 20
set before_cone [bounding cone]
set before_cylinder [bounding cylinder]
set move_rc [ttranslate cone cylinder 13 -7 5]
set after_cone [bounding cone]
set after_cylinder [bounding cylinder]
set witness_error 0.0
foreach before [list $before_cone $before_cylinder] after [list $after_cone $after_cylinder] {
  for {set i 0} {$i < 6} {incr i} {
    set axis_delta [lindex {13 -7 5 13 -7 5} $i]
    set e [expr {abs(([lindex $after $i]-[lindex $before $i])-$axis_delta)}]
    if {$e > $witness_error} {set witness_error $e}
  }
}
puts "M33615_TRANSLATE rc={$move_rc} cone_before={$before_cone} cone_after={$after_cone} cylinder_before={$before_cylinder} cylinder_after={$after_cylinder} witness_error=$witness_error"
if {$witness_error > 1.0e-7} {error "common translation witness did not match requested vector"}
puts "__BENCH_ASSERT_PASS__ transform_witness"
explode cylinder f
explode cone f
don cylinder_1 cone_1
bclearobjects
bcleartools
baddobjects cone_1
baddtools cylinder_1
bfillds
bbuild result
checknbshapes result -vertex 5 -edge 8 -wire 5 -face 4
puts "__BENCH_ASSERT_PASS__ official_topology"
