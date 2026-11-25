pload MODELING
plane p 0 0 0 0 0 1
mkface f1 p -10 10 -10 10
copy f1 f2
trotate f2 0 0 0 1 0 0 20
line l 0 0 0 0 1 0
mkedge e l -8 8
trotate e 0 0 0 1 0 0 10
settolerance e 1.5
bclearobjects
bcleartools
baddobjects f1 f2
baddtools e
bfillds
bbuild result
puts [checkshape result]
puts [nbshapes result]
foreach f [explode result f] {
    puts "$f [llength [explode $f w]] wire(s)"
    puts [sprops $f]
    foreach w [explode $f w] {
        puts "$w [llength [explode $w e]] edge(s)"
        puts [lprops $w]
    }
}
exit
