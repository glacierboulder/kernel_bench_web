# OCCT issue #690

Title: Segfault with a fillet on a curved base, sweep, and a curve in the opposite direction.

Public reproduction: restore `curved-base-sweep-curve-opposite-dir.brep`,
explode it, and run `blend result model 1 model_13`.  The expected behavior is
that the fillet returns a result; the base snapshot stops during the blend.

The issue is in the ChFi3d fillet path.
