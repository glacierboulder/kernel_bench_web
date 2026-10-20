set bf_case_id M21494_neighbor_sphere9p5
set bf_cone_radius 15.0
set bf_cone_height 10.0
set bf_sphere_radius 9.5
set bf_expected_curve_count 2
set bf_expected_point_count 0
set bf_expected_roots {{4.379957653105148 8.430063520342278} {9.466196193048699 0.800705710426951}}
source [file join [file dirname [file normalize [info script]]] m21494_intersection_oracle.tcl]
