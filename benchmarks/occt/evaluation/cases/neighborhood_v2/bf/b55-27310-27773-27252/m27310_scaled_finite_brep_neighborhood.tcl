pload TOPTEST
set here [file dirname [file normalize [info script]]]
source [file join $here .. bench_assertions.tcl]
set input_dir [file normalize [file join $here .. .. .. evaluator_tests occt-bf-group-b55-27310-27773-27252-oracle-v2 inputs]]
set input_a [file join $input_dir OCC496a.brep]
set input_b [file join $input_dir OCC496b.brep]
restore $input_a base_a
restore $input_b base_b
explode base_a f
explode base_b f
ttranslate base_b_2 1.8 0.5 0
mksurface baseline_surface_a base_a_8
mksurface baseline_surface_b base_b_2
set baseline_log [bopcurves base_a_8 base_b_2 -2d]
set baseline_curves [bench_curve_names c]
bench_assert {[llength $baseline_curves] == 1} "M27310 original BREP offset baseline has one intersection branch"
set baseline_uvs_a [bench_pcurve_samples c2d1_1]
set baseline_uvs_b [bench_pcurve_samples c2d2_1]
set baseline_curves [bench_rename_curves $baseline_curves b55_m27310_scale_baseline]
puts "BF_BASELINE_BOPCURVES_LOG_BEGIN"
puts $baseline_log
puts "BF_BASELINE_BOPCURVES_LOG_END"
restore $input_a a
restore $input_b b
tscale a 0 0 0 1.5
tscale b 0 0 0 1.5
explode a f
explode b f
ttranslate b_2 2.7 0.75 0
mksurface current_surface_a a_8
mksurface current_surface_b b_2
set log [bopcurves a_8 b_2 -2d]
if {[string first "3d curve" [whatis c]] >= 0} { renamevar c c_1 }
set curves [bench_curve_names c]
bench_assert {[llength $curves] == 1} "M27310 scaled finite-face neighborhood retains its single intersection branch"
bench_surface_transform_uv_samples baseline_surface_a current_surface_a $baseline_uvs_a 1.5 0.0 0.0 0.0 1.0e-5 \
  "M27310 first original BRep face"
bench_surface_transform_uv_samples baseline_surface_b current_surface_b $baseline_uvs_b 1.5 0.0 0.0 0.0 1.0e-5 \
  "M27310 second original BRep face"
puts "BF_BOPCURVES_LOG_BEGIN"
puts $log
puts "BF_BOPCURVES_LOG_END"
mksurface surface_a a_8
mksurface surface_b b_2
bench_intersection_support_mapping c $curves surface_a surface_b 1.5e-4 101
bench_finish
