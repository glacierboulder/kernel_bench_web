# Geometry-only predicates; execution, hashing and result parsing use the shared framework runtime.
namespace eval ::author20261110 {}
proc ::author20261110::mass {text} {
 if {![regexp {Mass\s*:\s*([-+0-9.eE]+)} $text all value] || ![::single20::finite $value]} {return {}}
 return $value
}
proc ::author20261110::count {text name} {
 if {![regexp [format {(^|
)\s*%s\s*:\s*([0-9]+)(\s|$)} $name] $text all prefix value]} {return -1}
 return $value
}
proc ::author20261110::close {value expected tolerance} {
 if {![::single20::finite $value]} {return 0}
 return [expr {abs($value-$expected)<=$tolerance}]
}
