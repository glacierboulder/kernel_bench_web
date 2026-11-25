pload MODELING
circle c1 0 0 0 0 -1 0 75
circle c2 0 0 0 0 -1 0 65
mkedge c1 c1
mkedge c2 c2
wire c1 c1
wire c2 c2
orientation c2 R
mkplane f1 c1 1
add c2 f1
prism p1 f1 0 1000 0
trotate p1 0 0 0 0 0 1 180
circle c3 50 500 -2000 0 0 1 50
mkedge c3 c3
wire c3 c3
mkplane f2 c3 1
prism p2 f2 0 0 4000
trotate p2 0 500 0 1 0 0 -77
trotate p2 0 0 0 0 0 1 180
bclearobjects
bcleartools
baddobjects p1
baddtools p2
bfillds
bbop cutResult 2
bbop sectionResult 4
puts [checkshape cutResult]
puts [nbshapes cutResult]
puts [vprops cutResult 1.0e-4]
puts [nbshapes sectionResult]
puts [checksection sectionResult -r 0]
puts [lprops sectionResult]
exit
