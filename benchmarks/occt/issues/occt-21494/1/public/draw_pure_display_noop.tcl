# External test-only compatibility adapter for the unchanged official Tcl tests
# in this bounded matrix. It replaces exactly five view/display-only DRAW
# commands and logs each invocation. No geometry command, assertion, expected
# value, or algorithm input is changed.
proc smallview {args} {
  puts "BF_DISPLAY_ADAPTER_NOOP command=smallview args=[list $args]"
}
proc don {args} {
  puts "BF_DISPLAY_ADAPTER_NOOP command=don args=[list $args]"
}
proc fit {args} {
  puts "BF_DISPLAY_ADAPTER_NOOP command=fit args=[list $args]"
}
proc disp {args} {
  puts "BF_DISPLAY_ADAPTER_NOOP command=disp args=[list $args]"
}
proc checkview {args} {
  puts "BF_DISPLAY_ADAPTER_NOOP command=checkview args=[list $args]"
}
