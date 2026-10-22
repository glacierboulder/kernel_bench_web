pload TOPTEST
set here [file dirname [file normalize [info script]]]
source [file join $here .. bench_assertions.tcl]
set input_dir [file normalize [file join $here .. .. .. evaluator_tests occt-bf-group-b2613378-27780-27252-21494-v1 inputs M27780_neighbor_translated_face]]
bench_m27780_case b261_m27780_scale \
  [file join $input_dir buc60532a.brep] [file join $input_dir buc60532b.brep] \
  1.5 0.05 0.0 0.0 0.0
bench_finish
