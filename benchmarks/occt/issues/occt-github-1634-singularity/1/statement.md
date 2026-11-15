# Keep a converged parameter hint on a collapsed surface boundary

A bilinear B-spline patch collapses one full parameter edge to a point. When the supplied parameter hint already maps to the query point, the next UV computation should preserve that hint. Validate the parameter pair and its geometric residual.

Upstream: https://github.com/Open-Cascade-SAS/OCCT/pull/1634
