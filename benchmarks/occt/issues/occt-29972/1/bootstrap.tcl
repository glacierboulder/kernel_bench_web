# Private v4 DRAW setup; files are resolved relative to this issue directory.
set ::v4_assertions 0
set ::v4_numeric_assertions 0
pload TOPTEST
set ::v4_casroot $::env(CASROOT)
foreach ::v4_name {StandardCommands.tcl TestCommands.tcl CheckCommands.tcl} {
  source [file join $::v4_casroot src DrawResources $::v4_name]
}
set imagedir [file dirname [info script]]
set test_image no_image
foreach ::v4_visual {checkview v2d smallview don donly disp fit axo clpoles clknots} {
  if {[llength [info commands $::v4_visual]] > 0} {rename $::v4_visual v4_original_$::v4_visual}
  proc $::v4_visual {args} { }
}
proc stage3_assert {ok id detail} {
  set safe_detail [string map [list "\n" "|" "\r" ""] $detail]
  if {$ok} {puts "BENCH_ASSERT_PASS $id $safe_detail kind=expression"} else {puts "BENCH_ASSERT_FAIL $id $safe_detail kind=expression"}
  incr ::v4_assertions
}
proc v4_finish {} {
  puts {__BENCH_ORACLE_COMPLETE__}
  puts "BENCH_ORACLE_OK assertions=$::v4_assertions numeric_assertions=$::v4_numeric_assertions"
  puts "TEST_DONE assertions=$::v4_assertions numeric_assertions=$::v4_numeric_assertions"
}
rename ::puts ::v4_raw_puts
proc ::puts {args} {
  if {[llength $args] == 1 && [regexp {^__BENCH_ASSERT_(PASS|FAIL)__[[:space:]]+([^[:space:]]+)(.*)$} [lindex $args 0] -> status id detail]} {
    set ok [expr {$status eq "PASS"}]
    stage3_assert $ok $id [string trim $detail]
    return
  }
  return [uplevel 1 [linsert $args 0 ::v4_raw_puts]]
}

proc v4_section_oracle {shape expected_edges} {
  upvar #0 $shape $shape
  set v4_nb_info [nbshapes $shape]
  if {[regexp {EDGE +: +([-0-9.+eE]+)} $v4_nb_info -> v4_edge_count]} {
    set v4_edge_count [expr {int($v4_edge_count)}]
    puts "M29972_SECTION_EDGE_COUNT shape=$shape observed=$v4_edge_count expected=$expected_edges"
    stage3_assert [expr {$v4_edge_count == $expected_edges}] edge_count "observed=$v4_edge_count expected=$expected_edges"
  } else {
    puts "M29972_SECTION_EDGE_COUNT_UNPARSED shape=$shape nbshapes={$v4_nb_info}"
    stage3_assert 0 edge_count "not measured: nbshapes output={$v4_nb_info}"
  }
  checknbshapes $shape -edge $expected_edges
  set v4_section_report [checksection $shape -r 4]
  set v4_section_nbv -1
  if {[regexp {nb alone Vertices : ([-0-9.+eE]+)} $v4_section_report -> v4_section_nbv]} {
    set v4_section_nbv [expr {int($v4_section_nbv)}]
    set v4_endpoint_ok [expr {$v4_section_nbv >= 2}]
  } else {
    set v4_endpoint_ok 0
  }
  puts "M29972_SECTION_ENDPOINTS observed=$v4_section_nbv official_rule=at_least_2 report={$v4_section_report}"
  if {!$v4_endpoint_ok} {
    puts "Error : The section is closed. The result is possible to be better than on MASTER version. Please check carefully."
  }
  stage3_assert $v4_endpoint_ok section_endpoint_count "observed=$v4_section_nbv expected_at_least=2"
  set v4_pair_count 0
  set v4_pair_max 0.0
  set v4_pair_ok $v4_endpoint_ok
  if {$v4_endpoint_ok} {
    for {set v4_i 1} {$v4_i < $v4_section_nbv} {incr v4_i} {
      for {set v4_j [expr {$v4_i + 1}]} {$v4_j <= $v4_section_nbv} {incr v4_j} {
        distmini dd alone_$v4_i alone_$v4_j
        set v4_distance [dval dd_val]
        set v4_distance [expr {double($v4_distance)}]
        if {$v4_distance > $v4_pair_max} {set v4_pair_max $v4_distance}
        puts "M29972_SECTION_PAIR i=$v4_i j=$v4_j distance=$v4_distance official_max=3.0e-6"
        if {$v4_distance > 3.0e-6} {
          puts "Error: The distance between alone_$v4_i and alone_$v4_j is too big"
          set v4_pair_ok 0
        }
        incr v4_pair_count
      }
    }
  }
  set v4_expected_pairs [expr {$v4_section_nbv * ($v4_section_nbv - 1) / 2}]
  if {$v4_pair_count != $v4_expected_pairs || $v4_pair_count == 0} {set v4_pair_ok 0}
  puts "M29972_SECTION_DISTANCE pairs=$v4_pair_count expected_pairs=$v4_expected_pairs max_pair_distance=$v4_pair_max official_max=3.0e-6"
  stage3_assert $v4_pair_ok section_distance "pairs=$v4_pair_count expected_pairs=$v4_expected_pairs max_pair_distance=$v4_pair_max official_max=3.0e-6"
}
