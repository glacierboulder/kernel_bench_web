pload MODELING
box a 0 0 0 10 10 10
box b 20 0 0 10 10 10
bfuse r0 a b
bcut result r0 a
puts [nbshapes result]
puts [vprops result]
puts [checkshape result]
puts [bounding result]
