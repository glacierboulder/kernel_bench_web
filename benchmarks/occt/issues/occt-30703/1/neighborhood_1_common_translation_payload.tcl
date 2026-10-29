# Derived neighbor: common rigid translation of both exact official surfaces.
# Original fixture bytes are preserved; transform witness guards against a no-op.
foreach v4_visual {smallview donly fit checkview clpoles clknots} {
  set v4_saved_visual v4_original_$v4_visual
  if {[llength [info commands $v4_visual]] > 0 && [llength [info commands $v4_saved_visual]] == 0} {
    rename $v4_visual $v4_saved_visual
  }
  if {[llength [info commands $v4_visual]] == 0} {proc $v4_visual {args} {}}
}
proc Error: {args} { puts "M30703_OFFICIAL_COUNT_FAILURE [join $args { }]" }
restore [locate_data_file bug30703s1] s1
restore [locate_data_file bug30703s2] s2
puts "M30703_TYPES_BEFORE_s1=[whatis s1]"
puts "M30703_TYPES_BEFORE_s2=[whatis s2]"
svalue s1 0 0 v4_s1_x0 v4_s1_y0 v4_s1_z0
bounds s2 v4_u1 v4_u2 v4_v1 v4_v2
set v4_u1 [dval v4_u1]
set v4_u2 [dval v4_u2]
set v4_v1 [dval v4_v1]
set v4_v2 [dval v4_v2]
set v4_umid [expr {($v4_u1 + $v4_u2) / 2.0}]
set v4_vmid [expr {($v4_v1 + $v4_v2) / 2.0}]
svalue s2 $v4_umid $v4_vmid v4_s2_x0 v4_s2_y0 v4_s2_z0
set v4_s1_x0 [dval v4_s1_x0]; set v4_s1_y0 [dval v4_s1_y0]; set v4_s1_z0 [dval v4_s1_z0]
set v4_s2_x0 [dval v4_s2_x0]; set v4_s2_y0 [dval v4_s2_y0]; set v4_s2_z0 [dval v4_s2_z0]
set v4_transform_return [translate s1 s2 13 -7 5]
svalue s1 0 0 v4_s1_x1 v4_s1_y1 v4_s1_z1
svalue s2 $v4_umid $v4_vmid v4_s2_x1 v4_s2_y1 v4_s2_z1
set v4_s1_x1 [dval v4_s1_x1]; set v4_s1_y1 [dval v4_s1_y1]; set v4_s1_z1 [dval v4_s1_z1]
set v4_s2_x1 [dval v4_s2_x1]; set v4_s2_y1 [dval v4_s2_y1]; set v4_s2_z1 [dval v4_s2_z1]
set v4_e1 [expr {max(abs(($v4_s1_x1-$v4_s1_x0)-13),abs(($v4_s1_y1-$v4_s1_y0)+7),abs(($v4_s1_z1-$v4_s1_z0)-5))}]
set v4_e2 [expr {max(abs(($v4_s2_x1-$v4_s2_x0)-13),abs(($v4_s2_y1-$v4_s2_y0)+7),abs(($v4_s2_z1-$v4_s2_z0)-5))}]
puts "M30703_TRANSLATE_RETURN=$v4_transform_return s1_before=($v4_s1_x0,$v4_s1_y0,$v4_s1_z0) s1_after=($v4_s1_x1,$v4_s1_y1,$v4_s1_z1) s2_before=($v4_s2_x0,$v4_s2_y0,$v4_s2_z0) s2_after=($v4_s2_x1,$v4_s2_y1,$v4_s2_z1) s1_witness_error=$v4_e1 s2_witness_error=$v4_e2"
set v4_move1 [expr {sqrt(($v4_s1_x1-$v4_s1_x0)*($v4_s1_x1-$v4_s1_x0)+($v4_s1_y1-$v4_s1_y0)*($v4_s1_y1-$v4_s1_y0)+($v4_s1_z1-$v4_s1_z0)*($v4_s1_z1-$v4_s1_z0))}]
set v4_move2 [expr {sqrt(($v4_s2_x1-$v4_s2_x0)*($v4_s2_x1-$v4_s2_x0)+($v4_s2_y1-$v4_s2_y0)*($v4_s2_y1-$v4_s2_y0)+($v4_s2_z1-$v4_s2_z0)*($v4_s2_z1-$v4_s2_z0))}]
if {$v4_e1 > 1.0e-8 || $v4_e2 > 1.0e-8 || $v4_move1 < 1.0 || $v4_move2 < 1.0} { error "common translation did not move both surfaces by the requested vector" }
puts "__BENCH_ASSERT_PASS__ transform_witness"
set info [intersect res s1 s2]
set v4_count [llength $info]
puts "M30703_INFO_COUNT=$v4_count expected=1"
if {$v4_count == 1} { puts "__BENCH_ASSERT_PASS__ solution_count" } else { puts "__BENCH_ASSERT_FAIL__ solution_count observed=$v4_count expected=1" }
checklength res -l 22.9782037
if {[info exists ::res]} {
  set v4_len_report [length res 1.0e-4]
  if {[regexp {The +length +res +is +([-0-9.+eE]+)} $v4_len_report -> v4_length]} {
    set v4_expected 22.9782037
    set v4_rel [expr {abs($v4_length-$v4_expected)/$v4_expected}]
    puts "M30703_LENGTH_OBSERVED=$v4_length expected=$v4_expected relative_error=$v4_rel official_relative_limit=0.01"
    if {$v4_length > 0.0 && $v4_rel <= 0.01} { puts "__BENCH_ASSERT_PASS__ curve_length" } else { puts "__BENCH_ASSERT_FAIL__ curve_length observed=$v4_length expected=$v4_expected relative_error=$v4_rel" }
  } else { puts "M30703_LENGTH_REPORT_UNPARSED=$v4_len_report"; puts "__BENCH_ASSERT_FAIL__ curve_length no_numeric_length" }
} else { puts "M30703_LENGTH_NOT_MEASURED=no_res_object" }
