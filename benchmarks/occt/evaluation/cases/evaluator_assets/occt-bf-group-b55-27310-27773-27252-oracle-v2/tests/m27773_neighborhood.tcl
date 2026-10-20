pload TOPTEST
puts "BF_CASE=M27773_offset_neighborhood"
circle bf_circle 1 0 0 20
offset bf_offset bf_circle 10 0 0 1
cvalue bf_offset 0 x y z dx dy dz
set bf_offset_x [dval x]
set bf_offset_y [dval y]
set bf_offset_z [dval z]
puts "BF_OFFSET_CVALUE0=$bf_offset_x,$bf_offset_y,$bf_offset_z"
mkedge bf_offset_edge bf_offset
vertex bf_line_v1 0.5 35 0
vertex bf_line_v2 0.5 -35 0
edge bf_line bf_line_v1 bf_line_v2
bsection result bf_offset_edge bf_line
puts "BF_RESULT_TYPE=[whatis result]"
checknbshapes result -vertex 2
explode result v
puts "BF_EXPECT_VERTEX_COUNT=2"
set bf_vertex_coords [getcoords result_1 result_2]
puts "BF_VERTEX_COORDS_BEGIN"
puts $bf_vertex_coords
puts "BF_VERTEX_COORDS_END"
