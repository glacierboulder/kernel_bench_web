pload TOPTEST
puts "BF_CASE=M27773_non_offset_regression"
circle bf_circle 1 0 0 20
mkedge bf_circle_edge bf_circle
vertex bf_line_v1 0 25 0
vertex bf_line_v2 0 -25 0
edge bf_line bf_line_v1 bf_line_v2
bsection result bf_circle_edge bf_line
puts "BF_RESULT_TYPE=[whatis result]"
explode result v
puts "BF_EXPECT_VERTEX_COUNT=2"
set bf_vertex_coords [getcoords result_1 result_2]
puts "BF_VERTEX_COORDS_BEGIN"
puts $bf_vertex_coords
puts "BF_VERTEX_COORDS_END"
