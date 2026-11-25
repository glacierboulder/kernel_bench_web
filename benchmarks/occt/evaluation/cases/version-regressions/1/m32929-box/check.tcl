set here [file dirname [file normalize [info script]]]
source [file join $::env(BENCH_FROZEN_CASE_ROOT) evaluation cases single20 assertions.tcl]
pload MODELING
# Same native commands and order as the registered 32929-regression fixture.
box b 10 10 10
explode b E
blend result b 1 b_1
set native [file join $here live-result.brep]
set target [file join $here live-edge-1.brep]
set opposite [file join $here live-edge-7.brep]
save result $native
save b_1 $target
save b_7 $opposite

set lib $::env(CSF_OCCTLibPath)
set prefix [file dirname [file dirname [file dirname $lib]]]
set headers [file join $prefix include opencascade]
set program [file join $here geometry-check]
set diagnostics [exec $::env(BENCH_CXX) -std=c++17 -I$headers -L$lib -Wl,-rpath,$lib \
    [file join $here location.cxx] -lTKTopAlgo -lTKBRep -lTKG3d -lTKGeomBase -lTKMath -lTKernel -o $program 2>@1]
if {$diagnostics ne ""} {puts $diagnostics}
set audit [exec $program $target $opposite $native \
    [file join $here healthy-1-result.brep] [file join $here healthy-2-result.brep] \
    [file join $here opposite-result.brep]]
puts $audit
::single20::assert exact_input_edges [string match {*INPUT target=1 opposite=7*} $audit] endpoints
foreach role {native healthy-1 healthy-2} {
    ::single20::assert $role [string match "*CONTROL $role target=1 opposite=0 witnesses=26 wrong_target=0 wrong_opposite=6*" $audit] geometry
}
::single20::assert opposite_rejected [string match {*CONTROL opposite target=0 opposite=1 witnesses=26 wrong_target=6 wrong_opposite=0*} $audit] geometry
::single20::finish
