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
set baseline_log [bopcurves base_a_8 base_b_2 -2d]
set baseline_curves [bench_curve_names c]
bench_assert {[llength $baseline_curves] == 2} "M27310 original BREP baseline has two intersection branches"
set baseline_curves [bench_rename_curves $baseline_curves b55_m27310_translation_baseline]
puts "BF_BASELINE_BOPCURVES_LOG_BEGIN"
puts $baseline_log
puts "BF_BASELINE_BOPCURVES_LOG_END"
restore $input_a a
restore $input_b b
ttranslate a 73.0 -12.0 5.0
ttranslate b 73.0 -12.0 5.0
explode a f
explode b f
set log [bopcurves a_8 b_2 -2d]
if {[string first "3d curve" [whatis c]] >= 0} { renamevar c c_1 }
set curves [bench_curve_names c]
bench_assert {[llength $curves] == 2} "M27310 common rigid translation preserves both original intersection branches"
bench_curve_transform_set $curves $baseline_curves 1.0 73.0 -12.0 5.0 1.0e-4 101
puts "BF_BOPCURVES_LOG_BEGIN"
puts $log
puts "BF_BOPCURVES_LOG_END"
mksurface surface_a a_8
mksurface surface_b b_2
bench_intersection_support_mapping c $curves surface_a surface_b 1.0e-4 101
bench_finish
