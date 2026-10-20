# This adapter replaces only pure display calls after the geometric checks.
# smallview remains untouched so the official trailing headless view error is recorded.
foreach command {don fit disp display checkview} {
  proc $command {args} [format {puts "BF_DISPLAY_ADAPTER_NOOP command=%s args=[list $args]"} $command]
}
