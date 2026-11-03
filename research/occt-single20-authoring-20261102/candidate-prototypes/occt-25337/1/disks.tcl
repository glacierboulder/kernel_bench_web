# Exact equal-radius disk union/intersection areas and centroids.
source [file join [file dirname [info script]] .. .. assertions.tcl]
pload TOPTEST
lassign $::single20_case ox oy oz radius distance angle
set dx [expr {$distance*cos($angle)}]
set dy [expr {$distance*sin($angle)}]
circle first_circle $ox $oy $oz $radius
circle second_circle [expr {$ox+$dx}] [expr {$oy+$dy}] $oz $radius
mkedge first_edge first_circle
mkedge second_edge second_circle
wire first_wire first_edge
wire second_wire second_edge
mkplane first_face first_wire
mkplane second_face second_wire
set intersection_area 0.0
if {$distance < 2*$radius} {
    set intersection_area [expr {2*$radius*$radius*acos($distance/(2.0*$radius)) - 0.5*$distance*sqrt(4*$radius*$radius-$distance*$distance)}]
}
set union_area [expr {2*acos(-1)*$radius*$radius-$intersection_area}]
set expected_x [expr {$ox+0.5*$dx}]
set expected_y [expr {$oy+0.5*$dy}]
foreach operation {fuse common} expected_area [list $union_area $intersection_area] {
    set error_code [catch {
        bop first_face second_face
        bop$operation result
    } operation_log]
    if {[info exists ::single20_negative]} {
        switch $::single20_negative {
            input_only {copy first_face result}
            empty {compound result}
            duplicate {compound first_face second_face result}
            shifted {ttranslate result 2 3 4}
        }
    }
    ::single20::assert ${operation}_completed [expr {$error_code == 0}] "error=$error_code report=$operation_log"
    set validity_ok 0
    if {![catch {checkshape result} validity]} {
        set validity_ok [expr {[string first "This shape seems to be valid" $validity] >= 0}]
    }
    ::single20::assert ${operation}_valid $validity_ok "checkshape=$validity"
    set area_ok 0
    set centroid_ok 0
    set observed_area unknown
    set centroid_error unknown
    if {![catch {sprops result cx cy cz -full} properties] &&
        [regexp {Mass\s*:\s*([-+0-9.eE]+)} $properties unused observed_area] &&
        [::single20::finite $observed_area]} {
        set area_limit [expr {1e-7*$radius*$radius}]
        set area_ok [expr {abs($observed_area-$expected_area) <= $area_limit}]
        if {$expected_area == 0.0} {
            set centroid_ok [expr {abs($observed_area) <= $area_limit}]
            set centroid_error empty
        } elseif {![catch {set x [dval cx]; set y [dval cy]; set z [dval cz]}] &&
                  [::single20::finite $x] && [::single20::finite $y] && [::single20::finite $z]} {
            set centroid_error [expr {sqrt(pow($x-$expected_x,2)+pow($y-$expected_y,2)+pow($z-$oz,2))}]
            set centroid_ok [expr {$centroid_error <= 1e-7*$radius}]
        }
    }
    ::single20::assert ${operation}_area $area_ok "observed=$observed_area expected=$expected_area relative_scale_limit=1e-7*r^2" numeric
    ::single20::assert ${operation}_centroid $centroid_ok "distance=$centroid_error limit=1e-7*r" numeric
}
::single20::finish
