set bf_case_id M21494_regression_cone10_sphere9
set bf_cone_radius 10.0
set bf_cone_height 10.0
set bf_sphere_radius 9.0
set bf_expected_curve_count 2
set bf_expected_point_count 0
set bf_expected_roots {{1.0629960629940944 8.937003937005905} {8.937003937005905 1.0629960629940949}}
source [file join [file dirname [file normalize [info script]]] m21494_intersection_oracle.tcl]
