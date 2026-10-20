pload MODELING
set here [file dirname [info script]]
restore [file join $here solid.brep] body
explode body W
mkplane f body_18
prism p f 0 0 12
bclearobjects
bcleartools
baddobjects p
baddtools body
bfillds
bsimplify -f 1
bapibop res_simple 1
puts "TEST_DONE issue=544"
