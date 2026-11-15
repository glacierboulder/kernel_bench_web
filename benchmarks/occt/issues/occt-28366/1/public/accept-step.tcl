pload MODELING

puts "============"
puts "OCC28366"
puts "============"
puts ""
#############################################
# BOP Common fails with solid and planar face
#############################################

pload XDE

stepread [file join [file dirname [info script]] bug28366_fuselage.stp] a *
renamevar a_1 a

# Sew all the faces and make a solid.
explode a f
sewing shell 1.0e-6 a_1 a_2 a_3 a_4 a_5 a_6 a_7 a_8
mkvolume fuselage shell

# Make a xy-plane at the origin.
plane pln
mkface face pln


set failures 0
set baseline 0
foreach angle {0 37 90} {
  plane pln
  mkface face pln
  if {$angle != 0} {trotate face 0 0 0 0 0 1 $angle}
  set message [bcommon result face fuselage]
  set counts [nbshapes result]
  set props [sprops result 1e-8]
  if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} $props full area]} {
    puts "ERROR no area at angle $angle"
    exit 2
  }
  if {$angle == 0} {set baseline $area}
  set delta [expr {abs($area - $baseline) / max(1.0, abs($baseline))}]
  set valid [string match {*seems to be valid*} [checkshape result]]
  set clean [expr {![regexp -nocase {warning|error} $message]}]
  set nonempty [expr {$area > 0 && [regexp {FACE\s*:\s*[1-9]} $counts]}]
  set pass [expr {$valid && $clean && $nonempty && $delta <= 1e-4}]
  puts "angle=$angle area=$area relative_delta=$delta valid=$valid clean=$clean nonempty=$nonempty pass=$pass"
  if {!$pass} {incr failures}
}
if {$failures > 0} {puts "VERDICT geometry_fail"; exit 1}
puts "VERDICT pass"
exit 0
