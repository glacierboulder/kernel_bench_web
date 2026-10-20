# Partial reference patch control

This control replays the official partial reference patch on the same locked baseline. It repairs M30082 and M30202 while leaving M33541 without its change; M33541 still fails its two numeric volume oracles. The M33541 v2 public case bytes are identical to v1, so this result is case-hash reusable. This control covers the three original cases only, not the nine-check formal suite.
