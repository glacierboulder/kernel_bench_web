pload MODELING
restore [file join [file dirname [info script]] bug24094_face.brep] skin
plane p 183.6 0 0 1 0 0 0 1 0
mkface planeFace p
foreach {name options} {standard {} first-only {-n2d2}} {
    bsection res skin planeFace {*}$options
    puts "SECTION $name"
    puts [nbshapes res]
    puts [lprops res]
}
