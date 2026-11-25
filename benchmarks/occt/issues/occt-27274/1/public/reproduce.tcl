pload MODELING
pcylinder b1 50 145
tcopy b1 b2
trotate b2 0 0 0 1 0 0 45
bclearobjects
bcleartools
baddobjects b1
baddtools b2
bfillds
bbuild result
puts [checkshape result]
puts [nbshapes result -t]
puts [sprops result 1.0e-4]
exit
