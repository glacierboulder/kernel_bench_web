# View-only adapter for this headless matrix; it does not change geometry commands or assertions.
foreach command {smallview don fit disp display checkview} {
  proc $command {args} [format {puts "BF_DISPLAY_ADAPTER_NOOP command=%s args=[list $args]"} $command]
}
