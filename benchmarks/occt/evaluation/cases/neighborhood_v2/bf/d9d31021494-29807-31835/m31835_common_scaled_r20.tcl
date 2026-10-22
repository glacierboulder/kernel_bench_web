pload TOPTEST
source [file join [file dirname [file normalize [info script]]] .. bench_assertions.tcl]
bench_centered_three_cylinder_common d9_m31835_r20 20.0
bench_finish
