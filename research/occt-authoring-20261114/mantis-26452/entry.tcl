if {[catch {source [file join [file dirname [info script]] reproduce.tcl]} msg]} {puts stderr "RUN_ERROR: $msg";exit 1}
exit 0
