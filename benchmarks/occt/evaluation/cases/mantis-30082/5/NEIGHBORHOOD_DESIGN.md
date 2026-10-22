# Neighborhood matrix design and evidence notes

These six additions extend the existing NG-04R-v2 and NG-05T-v1 issue
neighborhoods. The detailed registration payload and run hashes are in
`/tmp/mantis-neighbor-descriptors.json`; raw outputs and per-file hashes are
indexed by `/tmp/mantis-neighbor-evidence-manifest.json`.

## Construction choices

- **M30082:** exercise two scales, two rigid poses, both operand orders, and
  20-point versus 1000-point distance sampling. The 20/1000 comparison is
  repeated on the same scenario and does not add a scenario. `explode` runs
  after transforming the root BREP; sampled support-surface points witness
  that scale, rotation, and translation actually reached the faces. Each
  residual must satisfy both reported-tolerance consistency and a physical
  cap derived from the issue's `6.5e-7` precision scaled to the model plus
  projection slack. A synthetic oversized reported tolerance verifies that
  changing the report cannot increase that cap.
- **M30202:** retain the empty-intersection oracle for the selected trimmed
  face pair under two scales and poses and both operand orders. A candidate
  SIGSEGV is recorded as an execution error, not a geometry-oracle rejection.
- **M33541:** use analytic cylinder/sphere overlap volumes at two scales and
  shared rigid poses, checking forward Cut/Common and reversed Cut as separate
  scenarios at each pose. This is four new scenes; with two existing scenes,
  M33541 totals six. Source primitives are scaled before their separation and
  common pose are applied.
- **M31602:** cover two scales and poses, both face orders, 201-point physical
  residuals, and the scaled branch length around the seam case.
- **M32850:** use analytic cylinder residuals, pairwise sampled branch
  distinctness, and the expected three-short/one-long normalized branch
  profile in both operand orders. Reverse branches receive the same analytic
  residual and pairwise distinctness checks as forward branches. This checks
  branch identity and domain coverage, not only count.

## Scenario accounting

Counts are per independent geometry/input-operation scene. Operand order and
scale/pose combinations count separately; repeated sample densities do not.
Including existing neighborhood scenes, issue totals remain within the
15-scenario cap: M30082 totals 12 across both group versions, M30202 5,
M33541 6, M31602 5, and M32850 5.

## Replay summary

All six trusted reference runs passed. The b5 candidate is rejected by the
M30082 physical residual oracle in both group versions and by the M32850 branch
profile oracle. The available M31602 and M33541 candidate runs pass; this
evidence does not claim those candidates were rejected. The M30202 A candidate
passes; a separate cross-source b5 run crashes in `bopcurves -2d` before any
assertion and is preserved as an execution error.

For M30082, dense sampling found maximum residuals about `2.45e-4` at scale
0.5 and `6.26e-4` at scale 2, near normalized curve parameter `0.969` and
`0.975`. Twenty-point maxima were only about `6.9e-8` and `4.5e-8`. The raw
`xdistcs` logs are listed individually in the evidence manifest.
