pload TOPTEST
set here [file dirname [file normalize [info script]]]
source [file join $here .. bench_assertions.tcl]
set input_dir [file normalize [file join $here .. .. .. evaluator_tests occt-bf-group-b55-27310-27773-27252-oracle-v2 inputs]]
bench_brep_27252_case b55_m27252_offset005 [file join $input_dir bug27221.brep] 1.0 0.05
bench_finish
