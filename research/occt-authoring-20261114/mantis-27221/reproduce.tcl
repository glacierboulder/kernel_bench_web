pload MODELING
puts "============"
puts "OCC27221"
puts "============"
puts ""
#######################################################################
# Regression vs. 6.7.0: bcut fails without notice
#######################################################################

restore [file join [file dirname [info script]] bug27221.brep] a
explode a
mkplane f a_2
prism p f -25 0 0 

bcut result a_1 p
puts [nbshapes result]
puts [checkshape result]
puts [vprops result]
puts [lprops result]


if {![regexp -line {^\s*SOLID\s*:\s*1\s*$} [nbshapes result]]} {error "wrong topology"}
if {![string match "*This shape seems to be valid*" [checkshape result]]} {error "invalid result"}
if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} [vprops result] match measured]} {error "missing measure"}
if {abs($measured-56860.2)>1} {error "unexpected measure"}
puts CASE_PASS
