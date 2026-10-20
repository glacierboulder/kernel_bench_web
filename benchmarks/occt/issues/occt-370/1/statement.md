# OCCT issue #370

Title: `GeomFill_CorrectedFrenet` hangs in some cases.

The supplied `reproduce.cpp` builds a four-point composite curve and calls
`GeomFill_CorrectedFrenet::SetCurve()`.  It should return; the base snapshot
does not terminate within the bounded evaluator timeout.
