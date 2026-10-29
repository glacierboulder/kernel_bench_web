# OCCT catalog naming and migration map

The catalog keeps stable issue, group, suite, source, and version identities for compatibility with existing results. This migration normalizes filesystem paths and task titles only. New issue directories use `issues/occt-<number>/<version>/`; group and suite directories include an explicit `new` or `legacy` segment and ordered issue numbers.

## New groups

| Group directory | Stable group ID | Issue IDs and versions, in member order | Suite directory (stable suite ID) |
|---|---|---|---|
| `groups/new/occt-30082-30202-33541/1.json` | `NG-04R-v2` | `mantis-30082@2`, `mantis-30202@2`, `mantis-33541@2` | `evaluation/suites/new/occt-30082-30202-33541/1.json` (`NG-04R-checks-v2`) |
| `groups/new/occt-30082-31602-32850/1.json` | `NG-05T-v1` | `mantis-30082@4`, `mantis-31602@2`, `mantis-32850@1` | `evaluation/suites/new/occt-30082-31602-32850/1.json` (`NG-05T-v1-checks`) |
| `groups/new/occt-21494-29807-31835/1.json` | `occt-bf-group-d9d310-21494-29807-31835` | `occt-21494@1`, `occt-29807@1`, `occt-31835@1` | `evaluation/suites/new/occt-21494-29807-31835/1.json` (`occt-bf-suite-d9d310-21494-29807-31835`) |
| `groups/new/occt-27310-27773-27252/1.json` | `occt-bf-group-b55-27310-27773-27252-oracle-v2` | `occt-27310@1`, `occt-27773@1`, `occt-27252@1` | `evaluation/suites/new/occt-27310-27773-27252/1.json` (`occt-bf-suite-b55-27310-27773-27252-oracle-v2`) |
| `groups/new/occt-21494-27252-27780/1.json` | `occt-bf-group-b2613378-27780-27252-21494-v1` | `occt-21494@2`, `occt-27252@2`, `occt-27780@1` | `evaluation/suites/new/occt-21494-27252-27780/1.json` (`occt-bf-suite-b2613378-27780-27252-21494-v1`) |

The public titles follow `OCCT · <ordered numbers>`. Issue identity IDs and source locks retain their original IDs and versions.

## Added single-issue tasks

| Group directory | Stable identity | Suite directory |
|---|---|---|
| `groups/new/occt-32721/1.json` | `occt-boolean-intersection-v4-mantis-32721` | `evaluation/suites/new/occt-32721/1.json` |
| `groups/new/occt-32942/1.json` | `occt-boolean-intersection-v4-mantis-32942` | `evaluation/suites/new/occt-32942/1.json` |
| `groups/new/occt-31404/1.json` | `occt-boolean-intersection-v4-mantis-31404` | `evaluation/suites/new/occt-31404/1.json` |
| `groups/new/occt-31470/1.json` | `occt-boolean-intersection-v4-mantis-31470` | `evaluation/suites/new/occt-31470/1.json` |
| `groups/new/occt-32470/1.json` | `occt-boolean-intersection-v4-mantis-32470` | `evaluation/suites/new/occt-32470/1.json` |
| `groups/new/occt-32502/1.json` | `occt-boolean-intersection-v4-mantis-32502` | `evaluation/suites/new/occt-32502/1.json` |
| `groups/new/occt-33244/1.json` | `occt-boolean-intersection-v4-mantis-33244` | `evaluation/suites/new/occt-33244/1.json` |
| `groups/new/occt-30703/1.json` | `occt-boolean-intersection-v4-mantis-30703` | `evaluation/suites/new/occt-30703/1.json` |
| `groups/new/occt-29972/1.json` | `occt-boolean-intersection-v4-mantis-29972` | `evaluation/suites/new/occt-29972/1.json` |
| `groups/new/occt-33615/1.json` | `occt-boolean-intersection-v4-mantis-33615` | `evaluation/suites/new/occt-33615/1.json` |

## Legacy groups

| Group directory | Stable group ID | Mode and members | Suite directory (stable suite ID) |
|---|---|---|---|
| `groups/legacy/occt-single-544/1.json` | `occt_boolean_single_544` | single: `occt-544@1` | `evaluation/suites/legacy/occt-single-544/1.json` (`occt-single-544`) |
| `groups/legacy/occt-group-544/1.json` | `occt_boolean_group_visible_544` | group: `occt-544@1` | `evaluation/suites/legacy/occt-group-544/1.json` (`occt-group-544`) |
| `groups/legacy/occt-active-544/1.json` | `occt_boolean_active_visible_544` | active: `occt-544@1` | `evaluation/suites/legacy/occt-active-544/1.json` (`occt-active-544`) |
| `groups/legacy/occt-group-544-506-847/1.json` | `occt_boolean_group_visible_544_506_847` | group: `occt-544@1`, `occt-506@1`, `occt-847@1` | `evaluation/suites/legacy/occt-group-544-506-847/1.json` (`occt-visible3`) |
| `groups/legacy/occt-group-690-693-172/1.json` | `occt_boolean_group_visible_690_693_172` | group: `occt-690@1`, `occt-693@1`, `occt-172@1` | `evaluation/suites/legacy/occt-group-690-693-172/1.json` (`occt-visible4`) |
| `groups/legacy/occt-group-370-872-1452/1.json` | `occt_boolean_group_visible_370_872_1452` | group: `occt-370@1`, `occt-872@1`, `occt-1452@1` | `evaluation/suites/legacy/occt-group-370-872-1452/1.json` (`occt-visible5`) |
| `groups/legacy/occt-group-690-693-172-370-1452/1.json` | `occt_boolean_group_visible_690_693_172_370_1452` | group: `occt-690@1`, `occt-693@1`, `occt-172@1`, `occt-370@1`, `occt-1452@1` | `evaluation/suites/legacy/occt-group-690-693-172-370-1452/1.json` (`occt-visible5all`) |

Legacy titles use `旧题 · OCCT <ordered numbers> · <单题|组合题|主动题>`. Group and suite IDs remain unchanged for historical run compatibility.

## Checkpoint presence audit

This is a static existence check, not a claim that all cases pass the OCCT geometry oracle. For every member in all five new groups, the selected suite contains at least one required `original`, one required `neighborhood`, and one required `regression` checkpoint, and every referenced case file exists in the bundle.

| New group | Issue versions | Original / neighborhood / regression checkpoints |
|---|---|---:|
| `NG-04R-v2` | 30082@2, 30202@2, 33541@2 | 3 / 3 / 3 |
| `NG-05T-v1` | 30082@4, 31602@2, 32850@1 | 3 / 3 / 3 |
| `occt-bf-group-d9d310-21494-29807-31835` | 21494@1, 29807@1, 31835@1 | 6 / 3 / 3 |
| `occt-bf-group-b55-27310-27773-27252-oracle-v2` | 27310@1, 27773@1, 27252@1 | 4 / 3 / 3 |
| `occt-bf-group-b2613378-27780-27252-21494-v1` | 21494@2, 27252@2, 27780@1 | 3 / 3 / 3 |

For the Mantis suites, original inputs live under each normalized `issues/occt-<number>/<version>/public/` path; neighborhood and regression cases live under `evaluation/cases/mantis-<number>/<version>/`. The BF suites keep their group-scoped trusted tests under `evaluation/cases/evaluator_tests/<stable-group-id>/`. The validation record lists the five independent freezes and all 49 dispatcher selections.

## Frozen evaluator compatibility

Catalog-facing Mantis case paths now use `issues/occt-<number>/...`; the snapshot adapter preserves compatibility with original `issues/mantis-<number>/...` paths. Generic freeze code resolves issue identity from catalog entries, maps those paths at the snapshot boundary, and records the aliases in `benchmark-snapshot/snapshot.json`. The five groups select `evaluation/cases/five_group_runtime` through their toolchain manifests; legacy groups retain the default evaluator runtime. Project-local G2/G3 runner copies now validate a configured Conda environment without a fixed environment-name default. Their dispatch and geometry-core hashes were updated; the environment-only changes and before/after hashes are in [evaluator environment portability](evaluation/provenance/evaluator-environment-portability.json). Geometry cases, expected values, and oracle predicates were not changed.

## Preserved archives

- Superseded `benchmarks/occt_intersection`: `$CADAI_ARCHIVE_ROOT/occt_intersection_<timestamp>/`; 882 files and 982,054,506 file bytes. Per-file hashes are in its `ARCHIVE-CHECKSUMS.json`.
- Pre-merge default bundle backup: `$CADAI_ARCHIVE_ROOT/occt-benchmark-premerge_<timestamp>/`; 73 files and 320,863 file bytes. Per-file hashes are in its `ARCHIVE-CHECKSUMS.json`.
- Original part2 source directory was left unchanged. Its source bundles and machine-local raw run evidence were moved outside the shareable project; hashes and restore location placeholders are in [external evidence archive](evaluation/provenance/external-evidence-archive.json). Pinned source IDs, commits, tree hashes, evaluator IDs and suite IDs remain in the active bundle.

See [integration validation record](evaluation/provenance/integration-validation.json) for catalog counts, default task registration, cache metadata, and validation boundaries.
