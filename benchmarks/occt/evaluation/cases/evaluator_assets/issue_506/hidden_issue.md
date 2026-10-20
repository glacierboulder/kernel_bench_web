# Hidden issue 506 — evaluator only

Title: `Bnd_BoundSortBox::Compare fails in some cases`.

The original report says that comparing the board's bounding box against a
single stored hole box returns no indices for `hole1.brep`, while the expected
result is one item, index 0. `hole0.brep` is the report's positive control and
returns the expected index. The evaluator-side C++ reproducer is
`private/evaluator_tests/issue_506_bndsort_repro.cpp`.

This issue is intentionally hidden from Tasks B/C agents. The input geometry,
this note, the reproducer, and fix metadata are evaluator-only.
