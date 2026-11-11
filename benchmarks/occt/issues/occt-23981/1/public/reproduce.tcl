puts {=== OCCT 23981 public reproduction ===}
set inputs [file join [file dirname [info script]] inputs]
if {![file isdirectory $inputs]} {set inputs [file dirname [info script]]}
pload MODELING
restore [file join $inputs bug23981_s1.draw] s1
restore [file join $inputs bug23981_s2.draw] s2
intersect i s1 s2
puts {=== curve i_1 to surface s1 ===}
puts [xdistcs i_1 s1 0 1 100]
puts {=== curve i_1 to surface s2 ===}
puts [xdistcs i_1 s2 0 1 100]
puts {=== curve i_2 to surface s1 ===}
puts [xdistcs i_2 s1 0 1 100]
puts {=== curve i_2 to surface s2 ===}
puts [xdistcs i_2 s2 0 1 100]

puts PUBLIC_REPRO_COMPLETE
