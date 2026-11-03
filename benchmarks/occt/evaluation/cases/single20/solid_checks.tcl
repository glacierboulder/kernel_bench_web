# Shared measurements use GProp and BndLib, independently of the repaired
# intersection routines. These checks do not prove full set equality.
proc ::single20::mass {command shape} {
    set text [uplevel #0 [list $command $shape -full]]
    if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} $text unused value] || ![::single20::finite $value]} {
        error "missing finite $command mass"
    }
    return $value
}

proc ::single20::bounds {shape} {
    if {[llength [info commands ::boundingstr]]} {
        uplevel #0 [list boundingstr $shape bx0 by0 bz0 bx1 by1 bz1]
    } else {
        uplevel #0 [list bounding $shape -extToler -nodraw -save bx0 by0 bz0 bx1 by1 bz1]
    }
    set result {}
    foreach coordinate {bx0 by0 bz0 bx1 by1 bz1} {
        set value [uplevel #0 [list dval $coordinate]]
        if {![::single20::finite $value]} {error "non-finite bounding box"}
        lappend result $value
    }
    return $result
}

proc ::single20::solid_result {id shape expected_area area_limit expected_volume volume_limit allowed_bounds} {
    set valid 0
    set description unavailable
    if {![catch {uplevel #0 [list checkshape $shape]} description]} {
        set valid [expr {[string first "This shape seems to be valid" $description] >= 0}]
    }
    ::single20::assert ${id}_valid $valid "checkshape=$description"
    set solids {}
    catch {set solids [uplevel #0 [list explode $shape so]]}
    ::single20::assert ${id}_solid_count [expr {[llength $solids] == 1}] "observed=[llength $solids] expected=1" numeric
    set area unknown
    set area_ok 0
    if {![catch {set area [::single20::mass sprops $shape]}]} {
        set area_ok [expr {abs($area-$expected_area) <= $area_limit}]
    }
    ::single20::assert ${id}_area $area_ok "observed=$area expected=$expected_area limit=$area_limit" numeric
    set volume unknown
    set volume_ok 0
    if {![catch {set volume [::single20::mass vprops $shape]}]} {
        if {$expected_volume eq "positive"} {
            set volume_ok [expr {$volume > 1e-7}]
        } else {
            set volume_ok [expr {abs($volume-$expected_volume) <= $volume_limit}]
        }
    }
    ::single20::assert ${id}_volume $volume_ok "observed=$volume expected=$expected_volume limit=$volume_limit" numeric
    set bound_ok 1
    set measured unavailable
    if {[catch {
        uplevel #0 [list vprops $shape center_x center_y center_z -full]
        set measured [uplevel #0 {list [dval center_x] [dval center_y] [dval center_z]}]
    }]} {
        set bound_ok 0
    } else {
        for {set i 0} {$i < 3} {incr i} {
            set coordinate [lindex $measured $i]
            if {![::single20::finite $coordinate] || $coordinate < [lindex $allowed_bounds $i]-1e-5 ||
                $coordinate > [lindex $allowed_bounds [expr {$i+3}]]+1e-5} {
                set bound_ok 0
            }
        }
    }
    ::single20::assert ${id}_centroid_domain $bound_ok "centroid=$measured containing_input_box=$allowed_bounds limit=1e-5" numeric
}
