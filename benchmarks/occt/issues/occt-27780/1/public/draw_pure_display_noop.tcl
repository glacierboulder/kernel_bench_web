# Only pure display commands are replaced. The official view call remains active,
# keeping its exact trailing headless error after the geometry predicate.
foreach command {don checkview} {
  proc $command {args} [format {puts "BF_DISPLAY_ADAPTER_NOOP command=%s args=[list $args]"} $command]
}
