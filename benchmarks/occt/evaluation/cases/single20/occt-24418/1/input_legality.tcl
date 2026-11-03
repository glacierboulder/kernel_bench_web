set ::single20_case {0 0 0 0 0}
# M24418 programmatic upstream case. Direct torus/cone equations measure
# support error. Independently computed horizontal circle intersections check
# both sides of the closed branch, including the torus inner radial sheet.
source [file join [file dirname [info script]] .. .. assertions.tcl]
pload TOPTEST
lassign $::single20_case ox oy oz swapped separated
ptorus torus_shape 25 24 90
plane cone_axis 20 20 10 0 0 1
pcone cone_shape cone_axis 10 8 40
ttranslate torus_shape $ox $oy $oz
ttranslate cone_shape $ox $oy $oz
if {$separated} {ttranslate cone_shape 1000 0 0}
explode torus_shape f
explode cone_shape f
mksurface torus_support torus_shape_1
mksurface cone_support cone_shape_1
trimu torus_domain torus_support 0 1.5707963267948966
trimv cone_domain cone_support 0 40.049968789001575
set first torus_domain
set second cone_domain
if {$swapped} {set first cone_domain; set second torus_domain}
set validity [checkshape torus_shape]
::single20::assert valid_torus_shape [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
set validity [checkshape cone_shape]
::single20::assert valid_cone_shape [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
::single20::finish
