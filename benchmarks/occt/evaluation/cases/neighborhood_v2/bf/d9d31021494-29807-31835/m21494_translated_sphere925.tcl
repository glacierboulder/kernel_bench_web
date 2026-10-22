pload TOPTEST
source [file join [file dirname [file normalize [info script]]] .. bench_assertions.tcl]
bench_cone_sphere_case d9_m21494_translated 9.25 1.0 31.5 -17.25 8.0
bench_finish
