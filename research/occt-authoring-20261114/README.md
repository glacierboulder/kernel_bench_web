# OCCT benchmark submission

This revision registers **15 independent new tasks**, plus the #1177 expansion of existing task #172. The proposed catalog contains 70 entries, including the 54 entries in the base catalog.

- Boolean and intersection tasks: 24161, 24811, 25242, 25385, 25781, 25890-section, 25952-bopcurves, 29028, 31850-default.
- Fillet tasks: 32929, 1738, 1163, 1371, 1701, 1702. Some fillet issues specify an explicit failure as an acceptable result. The 1163 case is derived from the original chamfer input.
- The nine reference-only examples stay in this directory. They run successfully on the recorded OCCT 8.0.1 commit. A faulty source baseline for the same predicate has not been established.
- #1568 remains outside this submission. Controlled failure falls short of the upstream expectation of a completed fillet.

The nine Boolean candidate suites were replayed through the catalog case materializer and DRAW checkpoint driver against the recorded local OCE and OCCT Linux builds. The fillet suites retain the frozen B/F evidence in the original case packages. See individual reports for the precise scope, especially the derived Section and bopcurves cases.

See [SOURCE-BUNDLES.md](SOURCE-BUNDLES.md) for restoring the source commits before preparing the catalog source cache.
