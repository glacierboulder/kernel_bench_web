pload MODELING
pcylinder Cylinder 5 50 360
ptorus Torus 20 5 -180 180 360
trotate Torus 0 0 0 1 0 0 90
ttranslate Torus 20 0 0
puts OPERATION_STARTED
puts [bfuse Fusion Cylinder Torus]
puts [checkshape Fusion]
puts [nbshapes Fusion]
puts [vprops Fusion]
puts SCREEN_DONE
