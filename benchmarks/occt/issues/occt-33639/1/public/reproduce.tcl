pload TOPTEST
ptorus first 750 250 360
pcone second 200 0 2000
trotate second 0 0 0 1 0 0 90
ttranslate second 0 1000 0
bcut result first second
checkshape result
vprops result 1e-10 -full
