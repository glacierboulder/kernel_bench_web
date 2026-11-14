pload MODELING
puts "TODO OCC25983 ALL: Error :  is WRONG because number of"
puts "TODO OCC25983 ALL: Error : The area of result shape is"
puts "TODO OCC25983 ALL: Error : The volume of result shape is"

puts "========"
puts "OCC25983"
puts "========"
puts ""
##########################################
# Fusion of sweep and its mirror invalid
##########################################

restore [file join [file dirname [info script]] bug25983_deform-fusion1-tcl-BSpline.brep] BSpline
wire Knurling-0-spine BSpline
mksweep Knurling-0-spine
setsweep -FR
polyline DWire 0 0 0 1 -0.9999999999999998 0 1.0000000000000002 0.9999999999999998 0 0 0 0
trotate DWire 0 0 0 1 0 0 134.99999999999693
ttranslate DWire 9 0 0
addsweep DWire 
buildsweep Knurling -C -S
copy Knurling Clone
tmirror Clone 0 0 0 1 0 0
bfuzzyvalue 0.001
bcommon overlap Knurling Clone
puts INPUT
puts [vprops Knurling]
puts OVERLAP
puts [vprops overlap]
puts RESULT
bfuse result Knurling Clone

puts [checkshape result]
puts [nbshapes result]
puts [vprops result]


if {![regexp -line {^\s*SOLID\s*:\s*1\s*$} [nbshapes result]]} {error "wrong topology"}
if {![string match "*This shape seems to be valid*" [checkshape result]]} {error "invalid result"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [vprops result] match measured]} {error "missing measure"}
if {abs($measured-54.0383)>0.02} {error "unexpected measure"}
puts CASE_PASS
