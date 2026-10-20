# OCCT issue #693

Title: Segfault with a fillet on a straight base, sweep, and a curve in the
opposite direction.

Public reproduction: restore `straight-base-sweep-curve-opposite-dir.brep`,
explode it, and run `blend result model 1 model_5`.  The expected behavior is
that the fillet returns a result; the base snapshot stops during the blend.

This is the minimal companion to #690 and exercises the same ChFi3d
intersection path.
