# OCCT issue #872

Title: `BRepBuilderAPI_GTransform` face stretch crash.

The public `stretchError.brep` is read, its first face is transformed with an
affinity of `0.75000000000002087` about `(800,625,183)`, and the operation is
expected to return a shape without a construction error.
