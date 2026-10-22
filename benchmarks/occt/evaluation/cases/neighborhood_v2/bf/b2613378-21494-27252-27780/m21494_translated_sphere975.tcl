pload TOPTEST
source [file join [file dirname [file normalize [info script]]] .. bench_assertions.tcl]
bench_cone_sphere_case b261_m21494_translated 9.75 1.0 -23.0 41.5 6.25
bench_finish
