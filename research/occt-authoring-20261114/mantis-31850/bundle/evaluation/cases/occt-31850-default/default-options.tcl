pload MODELING
restore [file join [file dirname [info script]] inputs bug31850.brep] s
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

foreach {name expected} {r0 472.152 r1 37939.8 r2 2516.56 r3 34951.1 r4 203.491 rgf 37939.8} {
 if {![string match "*This shape seems to be valid*" [checkshape $name]]} {error "INVALID_SHAPE $name"}
 set measurement [expr {$name eq "r4" ? [lprops $name] : [vprops $name]}]
 if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} $measurement match value]} {error "MISSING_MEASURE $name"}
 if {abs($value-$expected)>0.2} {error "WRONG_MEASURE $name $value expected $expected"}
}
if {![regexp -line {^\s*SOLID\s*:\s*3\s*$} [nbshapes rgf]]} {error WRONG_GENERAL_FUSE_SOLID_COUNT}
puts TEST_DONE

