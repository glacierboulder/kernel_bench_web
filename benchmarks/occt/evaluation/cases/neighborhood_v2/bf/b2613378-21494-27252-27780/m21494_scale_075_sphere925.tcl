pload TOPTEST
source [file join [file dirname [file normalize [info script]]] .. bench_assertions.tcl]
bench_cone_sphere_case b261_m21494_scale075 9.25 0.75 0.0 0.0 0.0
bench_finish
