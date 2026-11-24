pload MODELING
beziercurve parab 3 -10 0 0.995 0 0 -1.005 10 0 0.995
mkedge e parab
settolerance e 0.01
plane p 0 0 0 0 0 1
mkface f p -20 20 -20 20
bclearobjects
bcleartools
baddobjects e
baddtools f
bfillds
puts [bopinterf e f]
foreach v [bopnews v] {puts [pnt $v]}
exit
