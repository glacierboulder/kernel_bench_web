set bf_case_id M31835_offset5_neighbor
set bf_radius 100.0
set bf_length 400.0
set bf_offset 5.0
set bf_expected_first_volume 5333333.333333333
set bf_expected_volume 4665159.323256903
set bf_relative_volume_tolerance 2.0e-5
source [file join [file dirname [file normalize [info script]]] m31835_three_cylinder_oracle.tcl]
