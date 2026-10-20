# OCCT issue #1452

Title: Crash when applying a negative offset to a small-diameter circular
wire.

The public reproducer creates a 2 mm circular wire and calls
`BRepOffsetAPI_MakeOffset::Perform()` with the negative one-degree, 3 mm-taper
offset.  A nearby 2.01 mm diameter is a public positive control; the 2.00 mm
case must not crash.
