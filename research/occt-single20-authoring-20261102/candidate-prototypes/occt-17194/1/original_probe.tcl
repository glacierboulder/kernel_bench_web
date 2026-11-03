source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
circle arc 0 0 0 0 0 1 1 0 0 20
mkedge edge arc -pi/2 pi/2
prism face edge 50 0 30
plane plane_support 10 0 0 1 0 4
mkface plane_face plane_support
bsection result face plane_face
set edges [explode result e]
set length [::single20::mass lprops result]
set validity [checkshape result]
::single20::assert branch_count [expr {[llength $edges]==2}] "edges=[llength $edges] expected=2" numeric
::single20::assert section_length [expr {abs($length-15.8064)<=0.00005}] "length=$length upstream_rounded=15.8064" numeric
::single20::assert valid_result [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
::single20::finish
