pload TOPTEST
box b1 10 10 10
box b2 10.00000018 0 0 10 10 10
explode b2 f
copy b2_1 f
trotate f 0 5 5 0 1 0 10
mksurface s f
mkface f s -100 100 -100 100

bclearobjects
bcleartools
baddobjects b1 b2 f
bfillds
bbuild result
bopcheck result

checkshape result
