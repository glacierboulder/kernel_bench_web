set bf_case_id M31835_steinmetz_r80_regression
set bf_radius 80.0
set bf_length 200.0
set bf_offset 0.0
set bf_expected_first_volume 2730666.666666667
set bf_expected_volume 2399381.2485198025
set bf_relative_volume_tolerance 2.0e-6
source [file join [file dirname [file normalize [info script]]] m31835_three_cylinder_oracle.tcl]
