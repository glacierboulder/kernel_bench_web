pload MODELING
box a 10 10 10
box b 5 0 0 10 10 10
bcommon overlap a b
bfuse union a b
bcut remainder b a
foreach {name expected} {overlap 500 union 1500 remainder 500} {
 if {![string match "*This shape seems to be valid*" [checkshape $name]]} {error "INVALID_SHAPE $name"}
 if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [vprops $name] match value]} {error "MISSING_VOLUME $name"}
 if {abs($value-$expected)>0.001} {error "WRONG_VOLUME $name $value"}
}
puts TEST_DONE

