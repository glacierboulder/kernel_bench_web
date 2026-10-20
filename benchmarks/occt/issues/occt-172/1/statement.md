# OCCT issue #172

Title: Fillet can not round a face.

Public DRAW reproduction:

```tcl
pload MODELING
box Box 10 10 10
explode Box E
blend Fillet Box 5 Box_1 5 Box_3
```

The large radius should complete the fillet instead of leaving the result
unset.  This is a visible large-radius ChFi3d case.
