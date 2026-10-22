pload TOPTEST
source [file join [file dirname [file normalize [info script]]] .. bench_assertions.tcl]
proc check_near_tangent_offset {prefix} {
  set cx 3.0
  set radius 12.0
  set offset 5.0
  set effective_radius [expr {$radius+$offset}]
  set line_x [expr {$cx+$effective_radius-0.01}]
  set expected_y [expr {sqrt($effective_radius*$effective_radius-($line_x-$cx)*($line_x-$cx))}]
  uplevel #0 [list circle ${prefix}_circle $cx 0 0 $radius]
  uplevel #0 [list offset ${prefix}_offset ${prefix}_circle $offset 0 0 1]
  uplevel #0 [list mkedge ${prefix}_offset_edge ${prefix}_offset]
  uplevel #0 [list vertex ${prefix}_line_v1 $line_x 5 0]
  uplevel #0 [list vertex ${prefix}_line_v2 $line_x -5 0]
  uplevel #0 [list edge ${prefix}_line ${prefix}_line_v1 ${prefix}_line_v2]
  uplevel #0 [list bsection ${prefix}_result ${prefix}_offset_edge ${prefix}_line]
  puts "BF_SECTION_TYPE_${prefix}=[uplevel #0 [list whatis ${prefix}_result]]"
  uplevel #0 [list checknbshapes ${prefix}_result -vertex 2]
  uplevel #0 [list explode ${prefix}_result v]
  set vertices 0
  for {set i 1} {$i <= 8} {incr i} {
    if {[catch {uplevel #0 [list whatis ${prefix}_result_$i]} kind] || ![regexp -nocase {vertex} $kind]} { break }
    incr vertices
  }
  bench_assert {$vertices == 2} "$prefix near-tangent crossing retains two distinct vertices"
  set ys {}
  for {set i 1} {$i <= $vertices} {incr i} {
    set coords [uplevel #0 [list getcoords ${prefix}_result_$i]]
    if {![regexp {\(x,y,z\)[[:space:]]*:[[:space:]]*([-+0-9.eE]+)[[:space:]]+([-+0-9.eE]+)[[:space:]]+([-+0-9.eE]+)} $coords -> x y z]} {
      bench_assert {0} "$prefix near-tangent vertex coordinates are readable"
      continue
    }
    bench_assert_close $x $line_x 1.0e-6 "$prefix near-tangent vertex lies on the input line"
    bench_assert_close [expr {abs($y)}] $expected_y 1.0e-4 "$prefix near-tangent vertex matches analytic circle equation"
    bench_assert_close $z 0.0 1.0e-7 "$prefix near-tangent vertex lies in the circle plane"
    lappend ys $y
  }
  if {[llength $ys] == 2} { bench_assert {[lindex $ys 0]*[lindex $ys 1] < 0.0} "$prefix near-tangent roots remain distinct" }
}
check_near_tangent_offset m27773_near_tangent
bench_finish
