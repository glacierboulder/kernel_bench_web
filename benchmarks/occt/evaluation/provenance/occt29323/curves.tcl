pload MODELING
set here [file dirname [info script]]
foreach tag {original translated rotated reversed} {
  restore [file join $here assets bug27615.brep] b
  explode b f
  copy b_1 f1
  copy b_19 f2
  if {$tag eq "translated"} {ttranslate f1 f2 6 -4 3}
  if {$tag eq "rotated"} {trotate f1 f2 0 0 0 0 0 1 19}
  if {$tag eq "reversed"} {
    set args {f2 f1 -2d -p 2. 0.085664915040461045 2.2023968513463648 29.150590232723459 -p 2.9507808705284453 0.085823752287563393 2.2023968513457164 31.082210390953925}
  } else {
    set args {f1 f2 -2d -p 2.2023968513463648 29.150590232723459 2. 0.085664915040461045 -p 2.2023968513457164 31.082210390953925 2.9507808705284453 0.085823752287563393}
  }
  set log [bopcurves {*}$args]
  puts "CURVE $tag $log"
  if {[regexp {Tolerance Reached=([-0-9.+eE]+)\s+([0-9]+)} $log _ tol n]} {
    puts "MEASURE $tag tolerance=$tol curves=$n"
  }
}
