pload MODELING
set inputDir [file dirname [info script]]
if {[file isdirectory [file join $inputDir inputs]]} {set inputDir [file join $inputDir inputs]}
restore [file join $inputDir bug31850.brep] s
explode s
bclearobjects
bcleartools
baddobjects s_1
baddtools s_2
bfillds
bbop r0 0
bbop r1 1
bbop r2 2
bbop r3 3
bbop r4 4
bbuild rgf

foreach name {r0 r1 r2 r3 r4 rgf} {
 puts "RESULT $name"
 puts [nbshapes $name]
 puts [checkshape $name]
 if {$name eq "r4"} {puts [lprops $name]} else {puts [vprops $name]}
}
puts PROBE_DONE
exit

