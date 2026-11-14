pload MODELING
box f1 10 10 10
plane p 0 0 5 0 0 1
mkface f2 p
bsection e f1 f2
puts [nbshapes e]
puts [checkshape e]
puts [lprops e]
puts SCREEN_DONE
