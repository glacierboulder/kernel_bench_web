source [file join [file dirname [info script]] bootstrap.tcl]
source [file join [file dirname [info script]] official_upstream.tcl]
stage3_assert 1 official_oracle_completed {unchanged upstream geometric checks reached completion}
v4_finish
