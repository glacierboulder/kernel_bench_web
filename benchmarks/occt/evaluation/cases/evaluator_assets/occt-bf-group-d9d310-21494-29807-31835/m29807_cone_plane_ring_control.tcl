# Hidden general-purpose cone/surface-intersection control for M29807.
# This is not claimed to reproduce the original double-cone degeneracy.
set bf_case_id M29807_cone_plane_ring_control
set bf_cone_base_radius 12.0
set bf_cone_top_radius 0.0
set bf_cone_height 24.0
set bf_plane_z 6.0
set bf_expected_z 6.0
set bf_expected_radius 9.0
set bf_expected_curve_count 1
set bf_expected_point_count 0
source [file join [file dirname [file normalize [info script]]] m29807_cone_plane_ring_oracle.tcl]
