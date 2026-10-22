# BF neighborhood v2: materials and dimensions

This folder contains 18 standalone DRAW checkpoints across the three later BF
groups. They cover 19 independent input scenarios because the M27773 radius
and line-parameter checkpoint runs two separately specified circle/line
scenarios. Scenario counts refer to distinct geometry inputs, not the number of
sample points used to measure residuals.

These are healthy mechanism neighborhoods: the natural F implementations are
expected to preserve the listed geometric invariants around the issue inputs.
They do not claim to reproduce the defect on every nearby input and are not
defect-preserving controls. Existing issue checks remain intact. Geometry
expected values are derived from analytic equations or the original BRep and
its explicit transforms, not from DSH output.

## Coverage

| Group / issue | Checkpoints / scenarios | Main dimensions |
| --- | ---: | --- |
| d9 / 21494 | 2 / 2 | scale and rigid translation; analytic cone/sphere double roots; two closed 3D intersection curves; sampled cone and sphere residuals |
| d9 / 29807 | 2 / 2 | cone-plane height and scale; one closed ring; analytic section radius; sampled plane and cone residuals |
| d9 / 31835 | 2 / 2 | three-cylinder common at radii 10 and 20; analytic volume; valid BOP/shape; one-solid topology |
| b55 / 27310 | 2 / 2 | original OCC496a/OCC496b BReps; common rigid translation and root scale; branch count; scaled source p-curve UV witnesses on each support; 3D/p-curve/support residuals |
| b55 / 27773 | 2 / 3 | offset-circle radius, offset amount, and line position; a near-tangent crossing; analytic roots; two distinct section vertices |
| b55 / 27252 | 2 / 2 | original bug27221 BRep; plane offset and scale; branch/curve transform; p-curve mapping residuals on both supports |
| b2613378 / 21494 | 2 / 2 | scale and rigid translation; analytic cone/sphere double roots; two closed curves; sampled support residuals |
| b2613378 / 27252 | 2 / 2 | original bug27221 BRep; plane offset and scale; branch/curve transform; p-curve mapping residuals on both supports |
| b2613378 / 27780 | 2 / 2 | original buc60532a/b BReps; relative face translation, common translation or scale; UV-to-physical-seed checks; selected-branch seed-distance invariant; 3D/p-curve/two-support residuals; endpoint direction |

The BRep scale and rigid-transform cases transform the root shapes before
exploding faces and extracting surfaces. For M27780 the `-p` arguments are the
two faces' UV coordinates. Rigid transforms preserve those UVs; scale cases
select the UV scaling factors only after checking `svalue` against the expected
transformed physical point on each source support. The known relative seed
separation is also checked before and after scale to retain the selected
branch correspondence.

For intersection mapping, the runner checks that each p-curve parameter domain
covers the 3D curve domain and evaluates both at the same `t`. It does not
normalize unrelated ranges to conceal truncation or parameter offset. The
M27252 F runs include a cylinder p-curve whose domain extends beyond the 3D
curve interval; direct shared-parameter sampling stays within the covered
interval. All p-curve-to-support checks evaluate actual 3D points and surface
points and record the maximum sampled residual.

## Calibration and limitations

Natural F calibration used F870 for d9 and b2613378, and e6afb for b55; commit,
tree, archive, and DRAW binary hashes are in the descriptor evidence. The
complete replay before adding fail-closed finite-number guards returned 18/18
successes. With the guards enabled, 17 cases completed and passed; the raw
25-second CPU default stopped the two-branch M27310 rigid-transform case with
SIGXCPU after its branch-count assertions. The formal suite configures CPU time
from the per-case timeout, and its frozen replay is the acceptance check for
that case.

The M27310 scaled case deliberately does not compare whole curves by a
Hausdorff threshold. Instead, it proves the transform on three original
p-curve UV samples on each real BRep support and independently checks the
result 3D curve's mappings to both supports. This samples the actual
intersection support, but does not claim dense whole-curve coverage.

The 3D/p-curve residuals are finite samples (typically 101 points, or 33 for
M27780); they establish the sampled geometric relation and parameter coverage,
not a formal global maximum bound between samples. The M27780 original inputs
remain the basis for scale/translation checks; independent synthetic
cylinder/plane geometry is not substituted for them.
