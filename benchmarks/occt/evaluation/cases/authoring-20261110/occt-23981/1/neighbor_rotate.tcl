set here [file dirname [info script]]
source [file join $here .. .. .. single20 assertions.tcl]
source [file join $here .. .. oracle_helpers.tcl]
set inputs [file normalize [file join $here .. .. .. .. .. issues occt-23981 1 public inputs]]
set inputs [file join $here inputs neighbor_rotate]
pload MODELING
restore [file join $inputs bug23981_s1.draw] s1
restore [file join $inputs bug23981_s2.draw] s2
intersect i s1 s2
::single20::assert two_curves [expr {([isdraw i_1] && [isdraw i_2] && ![isdraw i_3])}] branch_presence numeric
lassign {-347.773167083158 538.57646417050103 183.375 1 0 0 -0 1 0 -0 -0 1 44.194173824159201} cx cy cz ax ay az ux uy uz vx vy vz radius
set ok 1
set worst 0.0
set sample_count 0
for {set k 0} {$k<100} {incr k} {
 set parameter [expr {$k/99.0}]
 cvalue i_1 $parameter xx yy zz
 set x [dval xx]
 set y [dval yy]
 set z [dval zz]
 incr sample_count
 if {![::single20::finite $x] || ![::single20::finite $y] || ![::single20::finite $z]} {set ok 0;continue}
 set dx [expr {$x-$cx}]
 set dy [expr {$y-$cy}]
 set dz [expr {$z-$cz}]
 set u [expr {$dx*$ux+$dy*$uy+$dz*$uz}]
 set v [expr {$dx*$vx+$dy*$vy+$dz*$vz}]
 if {$v>=0} {set distance [expr {abs(sqrt($u*$u+$v*$v)-$radius)}]} else {set distance [expr {sqrt((abs($u)-$radius)*(abs($u)-$radius)+$v*$v)}]}
 if {$distance>1e-5} {set ok 0}
 if {$distance>$worst} {set worst $distance}
}
::single20::assert i_1_s1 [expr {$ok && $sample_count==100}] "analytic_support_samples=$sample_count max_distance=$worst limit=1e-5" numeric
lassign {-463.75990629028502 859 80.865093709715197 -0 -1 0 1 0 0 -0 0 1 186.78835506148999} cx cy cz ax ay az ux uy uz vx vy vz radius
set ok 1
set worst 0.0
set sample_count 0
for {set k 0} {$k<100} {incr k} {
 set parameter [expr {$k/99.0}]
 cvalue i_1 $parameter xx yy zz
 set x [dval xx]
 set y [dval yy]
 set z [dval zz]
 incr sample_count
 if {![::single20::finite $x] || ![::single20::finite $y] || ![::single20::finite $z]} {set ok 0;continue}
 set dx [expr {$x-$cx}]
 set dy [expr {$y-$cy}]
 set dz [expr {$z-$cz}]
 set u [expr {$dx*$ux+$dy*$uy+$dz*$uz}]
 set v [expr {$dx*$vx+$dy*$vy+$dz*$vz}]
 if {$v>=0} {set distance [expr {abs(sqrt($u*$u+$v*$v)-$radius)}]} else {set distance [expr {sqrt((abs($u)-$radius)*(abs($u)-$radius)+$v*$v)}]}
 if {$distance>1e-5} {set ok 0}
 if {$distance>$worst} {set worst $distance}
}
::single20::assert i_1_s2 [expr {$ok && $sample_count==100}] "analytic_support_samples=$sample_count max_distance=$worst limit=1e-5" numeric
lassign {-347.773167083158 538.57646417050103 183.375 1 0 0 -0 1 0 -0 -0 1 44.194173824159201} cx cy cz ax ay az ux uy uz vx vy vz radius
set ok 1
set worst 0.0
set sample_count 0
for {set k 0} {$k<100} {incr k} {
 set parameter [expr {$k/99.0}]
 cvalue i_2 $parameter xx yy zz
 set x [dval xx]
 set y [dval yy]
 set z [dval zz]
 incr sample_count
 if {![::single20::finite $x] || ![::single20::finite $y] || ![::single20::finite $z]} {set ok 0;continue}
 set dx [expr {$x-$cx}]
 set dy [expr {$y-$cy}]
 set dz [expr {$z-$cz}]
 set u [expr {$dx*$ux+$dy*$uy+$dz*$uz}]
 set v [expr {$dx*$vx+$dy*$vy+$dz*$vz}]
 if {$v>=0} {set distance [expr {abs(sqrt($u*$u+$v*$v)-$radius)}]} else {set distance [expr {sqrt((abs($u)-$radius)*(abs($u)-$radius)+$v*$v)}]}
 if {$distance>1e-5} {set ok 0}
 if {$distance>$worst} {set worst $distance}
}
::single20::assert i_2_s1 [expr {$ok && $sample_count==100}] "analytic_support_samples=$sample_count max_distance=$worst limit=1e-5" numeric
lassign {-463.75990629028502 859 80.865093709715197 -0 -1 0 1 0 0 -0 0 1 186.78835506148999} cx cy cz ax ay az ux uy uz vx vy vz radius
set ok 1
set worst 0.0
set sample_count 0
for {set k 0} {$k<100} {incr k} {
 set parameter [expr {$k/99.0}]
 cvalue i_2 $parameter xx yy zz
 set x [dval xx]
 set y [dval yy]
 set z [dval zz]
 incr sample_count
 if {![::single20::finite $x] || ![::single20::finite $y] || ![::single20::finite $z]} {set ok 0;continue}
 set dx [expr {$x-$cx}]
 set dy [expr {$y-$cy}]
 set dz [expr {$z-$cz}]
 set u [expr {$dx*$ux+$dy*$uy+$dz*$uz}]
 set v [expr {$dx*$vx+$dy*$vy+$dz*$vz}]
 if {$v>=0} {set distance [expr {abs(sqrt($u*$u+$v*$v)-$radius)}]} else {set distance [expr {sqrt((abs($u)-$radius)*(abs($u)-$radius)+$v*$v)}]}
 if {$distance>1e-5} {set ok 0}
 if {$distance>$worst} {set worst $distance}
}
::single20::assert i_2_s2 [expr {$ok && $sample_count==100}] "analytic_support_samples=$sample_count max_distance=$worst limit=1e-5" numeric
::single20::finish
