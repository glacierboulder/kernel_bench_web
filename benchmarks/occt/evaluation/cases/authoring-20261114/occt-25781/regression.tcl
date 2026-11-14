pload MODELING
pcylinder Cylinder 5 50 360
ptorus Torus 20 5 -180 180 360
trotate Torus 0 0 0 1 0 0 90
ttranslate Torus 20 0 0
ttranslate Torus 100 0 0
puts OPERATION_STARTED
puts [bfuse Fusion Cylinder Torus]
puts [checkshape Fusion]
puts [nbshapes Fusion]
puts [vprops Fusion]
if {![string match "*This shape seems to be valid*" [checkshape Fusion]]} {error "INVALID_FUSION"}
if {![regexp -line {^\s*SOLID\s*:\s*2\s*$} [nbshapes Fusion]]} {error "WRONG_SOLID_COUNT"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [vprops Fusion] full v] || abs($v-(1000*acos(-1)*acos(-1)+1250*acos(-1)))>0.2} {error "WRONG_VOLUME"}
puts TEST_DONE
