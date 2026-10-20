# Issue 506 — `Bnd_BoundSortBox::Compare` misses an item in one case

`Bnd_BoundSortBox::Compare()` is used as a fast bounding-box filter. For the
supplied board and hole geometry, comparing the board box against the single
stored box from `hole1.brep` returns an empty index list, although the expected
result is one item, index `0`. The supplied `hole0.brep` is a positive control
and already follows the expected behavior on the base.

Expected output for both hole inputs:

```text
indices.Size(): 1
Index 0
```

The public issue input archive has been unpacked into this directory. Use
`reproduce.cpp` to exercise the low-level API directly; this is intentionally a
focused helper test, not a complete `BRepAlgoAPI` Boolean operation.
