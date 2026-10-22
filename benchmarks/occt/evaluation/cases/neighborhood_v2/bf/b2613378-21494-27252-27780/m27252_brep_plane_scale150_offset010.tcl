pload TOPTEST
set here [file dirname [file normalize [info script]]]
source [file join $here .. bench_assertions.tcl]
set input_dir [file normalize [file join $here .. .. .. evaluator_tests occt-bf-group-b2613378-27780-27252-21494-v1 inputs M27252_neighbor_translated_plane]]
bench_brep_27252_case b261_m27252_scale150 [file join $input_dir bug27221.brep] 1.5 0.10
bench_finish
