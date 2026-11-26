pload MODELING
plane p 0 0 0 0 0 1
trim t p -10 10 -10 10
convert s t
mkface a s
foreach {ny extent} {0 10 2 15} {
    plane q 0 0 0 1 $ny 0
    mkface b q -$extent $extent -$extent $extent
    puts "tilt=$ny raw=[bopcurves a b -2d]"
    set rows [split [dump c_1] "\n"]
    foreach line $rows {if {[regexp -nocase {poles|spline} $line]} {puts [string trim $line]}}
}
exit
