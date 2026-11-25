pload MODELING
set poles {}
for {set i 0} {$i <= 24} {incr i} {
    lappend poles $i 0 [expr {$i == 23 ? 0.1 : 0}]
}
beziercurve c 25 {*}$poles
mkedge lifted c
plane p 0 0 0 0 0 1
mkface sheet p -5 30 -5 5
bcommon result lifted sheet
puts [nbshapes result]
puts [lprops result]
exit
