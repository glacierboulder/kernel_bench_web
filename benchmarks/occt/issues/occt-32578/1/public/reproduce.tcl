pload MODELING
set inputDir [file dirname [info script]]
restore [file join $inputDir bug32578_face.brep] face
restore [file join $inputDir bug32578_edges.brep] edges
bfuzzyvalue 0.01
bclearobjects
bcleartools
baddobjects face
baddtools {*}[explode edges]
bfillds
puts [bsplit result]
if {![isdraw result]} {
    puts "No split result is available."
    exit
}
puts [checkshape result]
puts [bopcheck result]
puts [nbshapes result -t]
puts [sprops result 1.e-4]
exit
