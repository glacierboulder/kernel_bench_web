pload MODELING
line line1 0 0 0 0 0 1
mkedge e1 line1 0 10
line line2 0 0.5 0 0 0 1
mkedge e2 line2 0 10
vertex v1 0 0.25 0
settolerance v1 0.25
vertex v2 0 0.25 10
settolerance v2 0.25
bclearobjects
bcleartools
baddobjects e1 e2 v1 v2
bfillds
bbuild result
puts [checkshape result]
puts [nbshapes result]
puts [lprops result]
exit
