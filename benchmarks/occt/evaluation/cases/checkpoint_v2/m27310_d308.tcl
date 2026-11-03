# Independent d308 measurement; reported tolerance is diagnostic, never a target.
pload TOPTEST
set root [file normalize [file join [file dirname [info script]] .. .. ..]]
source [file join $root evaluation cases neighborhood_v2 bf bench_assertions.tcl]
set inputs [file join $root issues occt-27310 1 public inputs]
restore [file join $inputs OCC496a.brep] a
restore [file join $inputs OCC496b.brep] b
explode a f
explode b f
set log [bopcurves a_10 b_4 -2d]
puts "D308_BOP_LOG_BEGIN\n$log\nD308_BOP_LOG_END"
set names [bench_curve_names c]
if {[llength $names] == 0 && [string first "3d curve" [whatis c]] >= 0} {
  renamevar c c_1
  set names {c_1}
}
if {![regexp {Tolerance Reached=([-+0-9.eE]+)} $log -> reported]} {error "reported tolerance missing"}
puts "D308_REPORTED_TOLERANCE=$reported"
puts "D308_LEGACY_DIAGNOSTIC reference=6.9230965382090094e-6 relative_band=0.1 scored=0"
# This conservative rejection envelope is the same independent linear budget
# already used for the existing M27310 BREP support-mapping neighborhoods.
set limit 1.0e-4
set residual 0.0
set mapping 0.0
set measured 0
mksurface surface_a a_10
mksurface surface_b b_4
foreach c $names {
  regexp {_(\d+)$} $c -> index
  lassign [bench_curve_bounds $c] first last
  puts "D308_BRANCH=$index range=$first,$last start=[bench_curve_point $c $first] end=[bench_curve_point $c $last]"
  for {set i 0} {$i <= 100} {incr i} {
    set t [expr {$first+($last-$first)*$i/100.0}]
    lassign [bench_curve_point $c $t] x y z
    # Exact cylinder implicit distances, independent of reported_tolerance and
    # the patched intersector/projection. Parameters are locked input geometry.
    set da [expr {abs(sqrt(($x+31.35044670105)**2+($y-11.99999904633)**2)-2.0)}]
    set db [expr {abs(sqrt(($y+4.768371582031e-7)**2+($z-38.50001144409)**2)-13.999999523167158)}]
    set residual [bench_max $residual [bench_max $da $db]]
    incr measured
  }
  set mapping [bench_max $mapping [bench_pcurve_mapping_max $c c2d1_$index surface_a 101]]
  set mapping [bench_max $mapping [bench_pcurve_mapping_max $c c2d2_$index surface_b 101]]
}
set assertions 0
proc d308_assert {value id detail} {
  incr ::assertions
  puts "BENCH_ASSERT_[expr {$value ? {PASS} : {FAIL}}] $id $detail kind=expression"
}
d308_assert [expr {[bench_is_finite $reported] && $reported >= 0.0}] reported_value_valid "reported=$reported"
d308_assert [expr {$measured > 0}] nonempty_measurements "branches=[llength $names] samples=$measured"
d308_assert [expr {$residual <= $limit}] surface_residual "observed=$residual upper=$limit"
d308_assert [expr {$mapping <= $limit}] pcurve_mapping "observed=$mapping upper=$limit"
puts "D308_COVERAGE=unqualified independent_clipping_domain_and_boundary_events_required"
puts __BENCH_ORACLE_COMPLETE__
puts "BENCH_ORACLE_OK assertions=$assertions numeric_assertions=0"
puts "TEST_DONE assertions=$assertions numeric_assertions=0"
