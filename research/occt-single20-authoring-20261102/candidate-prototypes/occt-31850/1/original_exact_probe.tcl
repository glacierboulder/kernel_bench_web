source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
restore [file join [file dirname [info script]] bug31850.brep] input
explode input
bclearobjects
bcleartools
baddobjects input_1
baddtools input_2
bfillds
foreach code {0 2} operation {common cut} expected_volume {472.151 2516.56} {
    bbop result $code
    set validity [checkshape result]
    set volume [::single20::mass vprops result]
    set faces [explode result f]
    ::single20::assert ${operation}_valid [expr {[string first "This shape seems to be valid" $validity]>=0}] "checkshape=$validity faces=[llength $faces]"
    ::single20::assert ${operation}_volume [expr {abs($volume-$expected_volume)<=1e-4*$expected_volume}] "volume=$volume expected=$expected_volume upstream_checkprops_epsilon=1e-4 screen_only=1" numeric
}
::single20::finish
