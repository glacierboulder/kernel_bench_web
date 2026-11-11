set here [file dirname [info script]]
source [file join $here .. .. .. single20 assertions.tcl]
source [file join $here .. .. oracle_helpers.tcl]
set inputs [file normalize [file join $here .. .. .. .. .. issues occt-23981 1 public inputs]]
pload MODELING
plane s1 0 0 0 0 0 1
plane s2 0 0 0 1 0 0
intersect i s1 s2
::single20::assert line_exists [expr {[isdraw i]}] branch_presence numeric
set ok 1
set worst 0.0
set sample_count 0
for {set k 0} {$k<100} {incr k} {
 set parameter [expr {$k/99.0}]
 cvalue i $parameter xx yy zz
 set x [dval xx]
 set y [dval yy]
 set z [dval zz]
 incr sample_count
 if {![::single20::finite $x] || ![::single20::finite $y] || ![::single20::finite $z]} {set ok 0;continue}
 set distance [expr {abs($z)} ]
 if {$distance>1e-7} {set ok 0}
 if {$distance>$worst} {set worst $distance}
}
::single20::assert i_s1 [expr {$ok && $sample_count==100}] "analytic_support_samples=$sample_count max_distance=$worst limit=1e-7" numeric
set ok 1
set worst 0.0
set sample_count 0
for {set k 0} {$k<100} {incr k} {
 set parameter [expr {$k/99.0}]
 cvalue i $parameter xx yy zz
 set x [dval xx]
 set y [dval yy]
 set z [dval zz]
 incr sample_count
 if {![::single20::finite $x] || ![::single20::finite $y] || ![::single20::finite $z]} {set ok 0;continue}
 set distance [expr {abs($x)} ]
 if {$distance>1e-7} {set ok 0}
 if {$distance>$worst} {set worst $distance}
}
::single20::assert i_s2 [expr {$ok && $sample_count==100}] "analytic_support_samples=$sample_count max_distance=$worst limit=1e-7" numeric
::single20::finish
