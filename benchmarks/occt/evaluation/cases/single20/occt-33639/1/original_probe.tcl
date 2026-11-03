source [file join [file dirname [info script]] .. .. assertions.tcl]
source [file join [file dirname [info script]] .. .. solid_checks.tcl]
pload TOPTEST
ptorus first 750 250 360
pcone second 200 0 2000
trotate second 0 0 0 1 0 0 90
ttranslate second 0 1000 0
set error_code [catch {bcut result first second} operation_log]
set validity unavailable
catch {set validity [checkshape result]}
set solids {}
catch {compound result counted_result; set solids [explode counted_result so]}
set volume 0.0
catch {set volume [::single20::mass vprops result]}
::single20::assert valid [expr {[string first "This shape seems to be valid" $validity]>=0}] "validity=$validity error=$error_code report=$operation_log"
::single20::assert solid_count [expr {[llength $solids]==1}] "solids=[llength $solids]" numeric
::single20::assert volume [expr {$volume>0 && $volume<2*pow(acos(-1),2)*750*250*250}] "volume=$volume" numeric
foreach id {kept removed} x {750 0} y {0 750} expected {IN OUT} {
    point witness $x $y 0
    set ok 0
    set state unavailable
    if {[llength $solids]==1} {set state [bclassify [lindex $solids 0] witness 1e-7]; set ok [regexp "\\m${expected}\\M" $state]}
    ::single20::assert $id $ok "point=($x,$y,0) expected=$expected actual=$state"
}
::single20::finish
