pload MODELING
cylinder s1 4.999999999813 1.35836143386791 0.20975890778078 -1 0 0 0 0 1 10
cylinder s2 9.999999999813 9.1401960568287 0.11837300583107 0 -0.75870713028692 0.651431877061437 0 -0.651431877061437 -0.75870713028692 5
mkface f1 s1 0 2*pi -35 35
mkface f2 s2 0 2*pi -35 35
bsection result f1 f2
puts [nbshapes result]
puts [lprops result]
foreach edge [explode result e] {
    mkcurve curve $edge
    bounds curve u1 u2
    foreach surf {s1 s2} {puts [xdistcs curve $surf u1 u2 33]}
}
exit
