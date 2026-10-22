pload TOPTEST
source [file join [file dirname [file normalize [info script]]] .. bench_assertions.tcl]
bench_cone_plane_ring_case d9_m29807_scaled 1.75 7.0
bench_finish
