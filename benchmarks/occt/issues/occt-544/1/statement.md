# Infinite loop when Simplifying Fuse operation, CPU to 100%

When fusing the supplied shape with an extruded wire, the Boolean operation
completes but simplifying the result does not return and consumes CPU.

Expected: the simplify-enabled Fuse operation finishes and returns the merged
shape. Observed: the process continues consuming CPU instead of completing.

The attached `solid.brep` and `reproduce.tcl` contain the executable input and
reproduction sequence. The reproduction is intentionally batch/headless; the
original report's visualization commands are not required to trigger it.
