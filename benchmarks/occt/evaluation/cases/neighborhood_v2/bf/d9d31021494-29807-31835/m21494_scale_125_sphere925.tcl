pload TOPTEST
source [file join [file dirname [file normalize [info script]]] .. bench_assertions.tcl]
bench_cone_sphere_case d9_m21494_scale125 9.25 1.25 0.0 0.0 0.0
bench_finish
