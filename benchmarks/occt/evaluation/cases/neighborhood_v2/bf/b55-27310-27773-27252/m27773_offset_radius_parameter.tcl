pload TOPTEST
source [file join [file dirname [file normalize [info script]]] .. bench_assertions.tcl]
proc check_offset_section {prefix cx radius offset line_x line_half_length} {
  set effective_radius [expr {$radius+$offset}]
  set expected_y [expr {sqrt($effective_radius*$effective_radius-($line_x-$cx)*($line_x-$cx))}]
  uplevel #0 [list circle ${prefix}_circle $cx 0 0 $radius]
  uplevel #0 [list offset ${prefix}_offset ${prefix}_circle $offset 0 0 1]
  uplevel #0 [list mkedge ${prefix}_offset_edge ${prefix}_offset]
  uplevel #0 [list vertex ${prefix}_line_v1 $line_x $line_half_length 0]
  uplevel #0 [list vertex ${prefix}_line_v2 $line_x [expr {-$line_half_length}] 0]
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
  bench_assert {$vertices == 2} "$prefix crossing produces two section vertices"
  set observed_y {}
  for {set i 1} {$i <= $vertices} {incr i} {
    set coords [uplevel #0 [list getcoords ${prefix}_result_$i]]
    if {![regexp {\(x,y,z\)[[:space:]]*:[[:space:]]*([-+0-9.eE]+)[[:space:]]+([-+0-9.eE]+)[[:space:]]+([-+0-9.eE]+)} $coords -> x y z]} {
      bench_assert {0} "$prefix vertex coordinates are readable"
      continue
    }
    bench_assert_close $x $line_x 1.0e-7 "$prefix vertex $i lies on the input line x"
    bench_assert_close $z 0.0 1.0e-7 "$prefix vertex $i lies in the circle plane"
    bench_assert_close [expr {abs($y)}] $expected_y 1.0e-5 "$prefix vertex $i matches analytic circle/line intersection"
    lappend observed_y $y
  }
  if {[llength $observed_y] == 2} {
    bench_assert {[lindex $observed_y 0]*[lindex $observed_y 1] < 0.0} "$prefix roots lie on opposite sides of the circle center"
  }
}
check_offset_section m27773_radius20 1.0 20.0 10.0 0.5 35.0
check_offset_section m27773_radius18 -2.0 18.0 3.5 2.5 25.0
bench_finish
