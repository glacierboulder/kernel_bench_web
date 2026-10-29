set imagedir [file dirname [info script]]
set test_image no_image
proc Error: {args} { puts "Error: [join $args { }]" }
plane plane -5 0 4 -1 0 0
pcone cone plane 3 1 10
pcylinder cylinder 10 20
set before_cone [bounding cone]
set before_cylinder [bounding cylinder]
set rotate_rc [trotate cone cylinder 0 0 0 0 0 1 90]
set after_cone [bounding cone]
set after_cylinder [bounding cylinder]
set changed 0.0
foreach before [list $before_cone $before_cylinder] after [list $after_cone $after_cylinder] {
  for {set i 0} {$i < 6} {incr i} {
    set delta [expr {abs([lindex $after $i]-[lindex $before $i])}]
    if {$delta > $changed} {set changed $delta}
  }
}
puts "M33615_ROTATE_Z90 rc={$rotate_rc} cone_before={$before_cone} cone_after={$after_cone} cylinder_before={$before_cylinder} cylinder_after={$after_cylinder} bbox_change=$changed"
if {$changed < 1.0e-6} {error "common rotation did not change the input bounds"}
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
