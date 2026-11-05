# OCCT catalog naming and migration map

The catalog keeps stable issue, group, suite, source, and version identities for compatibility with existing results. Existing identities remain stable; the 2026-11-05 split adds twelve independent task/suite identities. New issue directories use `issues/occt-<number>/<version>/`; groups now use `single`, `multiple`, or `legacy`. Existing suites retain `new`/`legacy`; newly split suites use `single`.

## Preserved multiple groups

| Group directory | Stable group ID | Issue IDs and versions, in member order | Suite directory (stable suite ID) |
|---|---|---|---|
| `groups/multiple/occt-30082-30202-33541/1.json` | `NG-04R-v2` | `mantis-30082@2`, `mantis-30202@2`, `mantis-33541@2` | `evaluation/suites/new/occt-30082-30202-33541/1.json` (`NG-04R-checks-v2`) |
| `groups/multiple/occt-30082-31602-32850/1.json` | `NG-05T-v1` | `mantis-30082@4`, `mantis-31602@2`, `mantis-32850@1` | `evaluation/suites/new/occt-30082-31602-32850/1.json` (`NG-05T-v1-checks`) |
| `groups/multiple/occt-21494-29807-31835/1.json` | `occt-bf-group-d9d310-21494-29807-31835` | `occt-21494@1`, `occt-29807@1`, `occt-31835@1` | `evaluation/suites/new/occt-21494-29807-31835/1.json` (`occt-bf-suite-d9d310-21494-29807-31835`) |
| `groups/multiple/occt-27310-27773-27252/1.json` | `occt-bf-group-b55-27310-27773-27252-oracle-v2` | `occt-27310@1`, `occt-27773@1`, `occt-27252@1` | `evaluation/suites/new/occt-27310-27773-27252/2.json` (`occt-bf-suite-b55-27310-27773-27252-geometry-v2`) |
| `groups/multiple/occt-21494-27252-27780/1.json` | `occt-bf-group-b2613378-27780-27252-21494-v1` | `occt-21494@2`, `occt-27252@2`, `occt-27780@1` | `evaluation/suites/new/occt-21494-27252-27780/1.json` (`occt-bf-suite-b2613378-27780-27252-21494-v1`) |

The public titles follow `OCCT · <ordered numbers>`. Issue identity IDs and source locks retain their original IDs and versions.

## Added single-issue tasks

| Group directory | Stable identity | Suite directory |
|---|---|---|
| `groups/single/occt-32721/1.json` | `occt-boolean-intersection-v4-mantis-32721` | `evaluation/suites/new/occt-32721/1.json` |
| `groups/single/occt-32942/1.json` | `occt-boolean-intersection-v4-mantis-32942` | `evaluation/suites/new/occt-32942/1.json` |
| `groups/single/occt-31404/1.json` | `occt-boolean-intersection-v4-mantis-31404` | `evaluation/suites/new/occt-31404/1.json` |
| `groups/single/occt-31470/1.json` | `occt-boolean-intersection-v4-mantis-31470` | `evaluation/suites/new/occt-31470/1.json` |
| `groups/single/occt-32470/1.json` | `occt-boolean-intersection-v4-mantis-32470` | `evaluation/suites/new/occt-32470/1.json` |
| `groups/single/occt-32502/1.json` | `occt-boolean-intersection-v4-mantis-32502` | `evaluation/suites/new/occt-32502/1.json` |
| `groups/single/occt-33244/1.json` | `occt-boolean-intersection-v4-mantis-33244` | `evaluation/suites/new/occt-33244/1.json` |
| `groups/single/occt-30703/1.json` | `occt-boolean-intersection-v4-mantis-30703` | `evaluation/suites/new/occt-30703/1.json` |
| `groups/single/occt-29972/1.json` | `occt-boolean-intersection-v4-mantis-29972` | `evaluation/suites/new/occt-29972/1.json` |
| `groups/single/occt-33615/1.json` | `occt-boolean-intersection-v4-mantis-33615` | `evaluation/suites/new/occt-33615/1.json` |

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
| `NG-04R-v2` | 30082@2, 30202@2, 33541@2 | 3 / 6 / 3 |
| `NG-05T-v1` | 30082@4, 31602@2, 32850@1 | 3 / 6 / 3 |
| `occt-bf-group-d9d310-21494-29807-31835` | 21494@1, 29807@1, 31835@1 | 6 / 9 / 3 |
| `occt-bf-group-b55-27310-27773-27252-oracle-v2` | 27310@1, 27773@1, 27252@1 | 4 / 9 / 3 |
| `occt-bf-group-b2613378-27780-27252-21494-v1` | 21494@2, 27252@2, 27780@1 | 3 / 9 / 3 |

For the Mantis suites, original inputs live under each normalized `issues/occt-<number>/<version>/public/` path; neighborhood and regression cases live under `evaluation/cases/mantis-<number>/<version>/`. The BF suites keep their group-scoped trusted tests under `evaluation/cases/evaluator_tests/<stable-group-id>/`. The table counts the current five multiple suites (73 checkpoints). The historical integration-validation record lists five independent freezes and 49 earlier dispatcher selections; it is not a replay of the current suites.

## Frozen evaluator compatibility

Catalog-facing Mantis case paths now use `issues/occt-<number>/...`; the snapshot adapter preserves compatibility with original `issues/mantis-<number>/...` paths. Generic freeze code resolves issue identity from catalog entries, maps those paths at the snapshot boundary, and records the aliases in `benchmark-snapshot/snapshot.json`. The five groups select `evaluation/cases/five_group_runtime` through their toolchain manifests; legacy groups retain the default evaluator runtime. Project-local G2/G3 runner copies now validate a configured Conda environment without a fixed environment-name default. Their dispatch and geometry-core hashes were updated; the environment-only changes and before/after hashes are in [evaluator environment portability](evaluation/provenance/evaluator-environment-portability.json). Geometry cases, expected values, and oracle predicates were not changed.

## Preserved archives

- Superseded `benchmarks/occt_intersection`: `$CADAI_ARCHIVE_ROOT/occt_intersection_<timestamp>/`; 882 files and 982,054,506 file bytes. Per-file hashes are in its `ARCHIVE-CHECKSUMS.json`.
- Pre-merge default bundle backup: `$CADAI_ARCHIVE_ROOT/occt-benchmark-premerge_<timestamp>/`; 73 files and 320,863 file bytes. Per-file hashes are in its `ARCHIVE-CHECKSUMS.json`.
- Original part2 source directory was left unchanged. Its source bundles and machine-local raw run evidence were moved outside the shareable project; hashes and restore location placeholders are in [external evidence archive](evaluation/provenance/external-evidence-archive.json). Pinned source IDs, commits, tree hashes, evaluator IDs and suite IDs remain in the active bundle.

See [integration validation record](evaluation/provenance/integration-validation.json) for catalog counts, default task registration, cache metadata, and validation boundaries.

## 2026-11-05 去重单题与目录调整

`groups/new/` 已调整为 `groups/single/`；五个三 issue 原组合题移至 `groups/multiple/`。现有 30 个单题保持身份，新增 12 个去重单题，因此 single 目录共 42 道不同 issue，multiple 目录保留 5 个组合题，legacy 保留 7 个任务；全 catalog 共 54 issue versions、54 tasks、55 suites、19 source identities。

去重按规范 issue ID，重复的 30082、21494、27252 各只新增一个 single task。采用拆分前 catalog 首次出现的成员版本，保持该版本的 B baseline；不合并不同 baseline 的检查点。未选版本仍在 multiple 中保留。新 task ID 为 `occt-single-<number>`，suite ID 为 `occt-single-<number>-checks@1`，suite 路径为 `evaluation/suites/single/occt-<number>/1.json`。旧 suite 仍位于 `evaluation/suites/new/`，其身份、定义和历史快照保留。

| Issue | 选用版本 | 来源 group | 检查点 |
| --- | --- | --- | ---: |
| mantis-30082 | 2 | `NG-04R-v2` | 4 |
| mantis-30202 | 2 | `NG-04R-v2` | 4 |
| mantis-33541 | 2 | `NG-04R-v2` | 4 |
| mantis-31602 | 2 | `NG-05T-v1` | 4 |
| mantis-32850 | 1 | `NG-05T-v1` | 4 |
| occt-21494 | 1 | `occt-bf-group-d9d310-21494-29807-31835` | 5 |
| occt-29807 | 1 | `occt-bf-group-d9d310-21494-29807-31835` | 7 |
| occt-31835 | 1 | `occt-bf-group-d9d310-21494-29807-31835` | 6 |
| occt-27310 | 1 | `occt-bf-group-b55-27310-27773-27252-oracle-v2` | 6 |
| occt-27773 | 1 | `occt-bf-group-b55-27310-27773-27252-oracle-v2` | 5 |
| occt-27252 | 1 | `occt-bf-group-b55-27310-27773-27252-oracle-v2` | 5 |
| occt-27780 | 1 | `occt-bf-group-b2613378-27780-27252-21494-v1` | 5 |

新增 single suites 继承各自来源当前 suite 中该 issue 的全部检查点、runner options、support files 和哈希固定的运行依赖，共 59 条（16 original、31 neighborhood、12 regression）。M27310 使用 geometry-v2 的 d308；覆盖参考仍待确认时保留 INCONCLUSIVE，拆分不授予新的几何通过资格。

当前 54 个 task 引用 54 个不同 suite，共 274 条 required checkpoint：42 个 single tasks 为 179 条，5 个 multiple tasks 为 73 条，7 个 legacy tasks 为 22 条。全部 55 个注册 suite 共 290 条（91 original、139 neighborhood、60 regression），包括未被当前 task 引用的旧 B55 oracle-v2 的 16 条。这里累计 suite 清单行，single 与 multiple 存在复用覆盖，不能视为独立几何 case 数。

[机器可读拆分来源](evaluation/provenance/single-split-20261105.json) 记录选择、未选版本、目录移动和检查点映射。本次执行清单、材料冻结及路由测试，没有重建 OCCT、重放几何或调用模型。路径变化会改变公开任务材料哈希；已有数据库的同 ID/version 再导入可能触发冲突，应按现有冲突保护逐项处理，不清库或覆盖历史结果。本次未修改运行数据库。
