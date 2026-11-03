source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
# cylinder r = 8, z = 0..30
pcylinder c 8 30

# helix: 2D line u = t, v = t * pitch / (2 pi) on a cylindrical surface r = 8,
# pitch 2, 7.5 turns (height 15), as one edge with its 3D curve built
cylinder cs 0 0 0 0 0 1 8
line l 0 0 1 0.3183098861837907
mkedge e l cs 0 49.4536246421342
wire spine e
build3d spine

# profile: circle r = 0.6 at the spine start, normal along the spine tangent
circle pc 8 0 0 0 0.9528905 0.3033145 0.6
mkedge pe pc
wire prof pe

# sweep with a fixed +Z binormal, round-corner transitions, as a solid
mksweep spine
setsweep -CN 0 0 1
addsweep prof
buildsweep tool -R -S

# DZ = 16.2: the tool starts inside the cylinder and exits the top face at
# theta = 324 degrees from the seam. Before the fix nothing was removed here
# (volume stayed 6031.86); DZ = 16.0 worked.
ttranslate tool 0 0 16.2


foreach input {c tool} {
    set validity [checkshape $input]
    if {[string first "This shape seems to be valid" $validity]<0} {error "input is invalid: $input $validity"}
}
set input_volume [::single20::mass vprops c]
set tool_volume [::single20::mass vprops tool]
bcut result c tool
set volume [::single20::mass vprops result]
set validity [checkshape result]
set solids [explode result so]
set removed [expr {$input_volume-$volume}]
::single20::assert valid_result [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity"
::single20::assert single_solid [expr {[llength $solids]==1}] "solids=[llength $solids]" numeric
::single20::assert removal_screen [expr {$removed>100.0 && $removed<min(400.0,$tool_volume)}] "removed=$removed input_volume=$input_volume tool_volume=$tool_volume screen_only=1" numeric
::single20::finish
