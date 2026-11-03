pload TOPTEST
circle c 0 0 0 0 0 1 1 0 0 100
extsurf s1 c 0 0 1
plane s2 0 0 0 1 0 0 0 1 0
mkface b1 s1
mkface b2 s2
bopcurves b1 b2
