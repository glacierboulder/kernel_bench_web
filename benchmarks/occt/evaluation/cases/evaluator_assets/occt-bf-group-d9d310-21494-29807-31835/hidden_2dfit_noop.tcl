# Hidden-calibration-only compatibility for the verified 2D viewer-fit command.
# B/F source review confirms this only changes 2D view fit/zoom/repaint/title.
# Does not replace or alter any geometry command or official test predicate.
proc 2dfit {args} {
  puts "BF_HIDDEN_2DFIT_ADAPTER_NOOP command=2dfit args=[list $args]"
}
