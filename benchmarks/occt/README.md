# OCCT shared benchmark bundle

This is the default OCCT catalog. It contains 42 unique single-issue tasks, 5 preserved multi-issue tasks, and 7 legacy tasks: 54 tasks and 55 suites. The 47 research tasks use the shared framework runtime.

Single tasks use `groups/single/occt-N/1.json`; the five original three-member tasks use `groups/multiple/occt-N-N-N/1.json`. Newly split suites use `evaluation/suites/single/occt-N/1.json`; existing suites retain `evaluation/suites/new/` paths. Issue directories use `issues/occt-N/<version>/`. Display names use `OCCT · N / N...`. Historical identity IDs remain stable so saved runs and frozen evidence retain their original identity.

`benchmarks/occt` is the only active benchmark directory. Import copies belong under ignored `data/imports/`; execution evidence belongs under `data/`. Reports are collected under `CADAI/tmp/kernel_bench_web_report/` and named `<object>_<content>_<YYYYMMDD>.md`.

The five multi-issue tasks use the following catalog group IDs.

- NG-04R-v2 — 新题 · OCCT 30082 / 30202 / 33541
- NG-05T-v1 — 新题 · OCCT 30082 / 31602 / 32850
- occt-bf-group-d9d310-21494-29807-31835 — 新题 · OCCT 21494 / 29807 / 31835
- occt-bf-group-b55-27310-27773-27252-oracle-v2 — 新题 · OCCT 27310 / 27773 / 27252
- occt-bf-group-b2613378-27780-27252-21494-v1 — 新题 · OCCT 21494 / 27252 / 27780

The bundle includes pinned source-lock records, evaluator assets, provenance, and toolchain profiles. It contains no checkout or runtime cache. The two original Git bundle archives and machine-local raw run evidence are preserved in an external archive; their hashes and restore placeholder are recorded in evaluation/provenance/external-evidence-archive.json. Workers prepare the locked source cache from a local Git repository. Mantis suite case paths are canonicalized in the catalog and mapped at freeze time to evaluator dispatch keys.

Each new group is runnable independently from its group manifest and compatible suite. See [directory and identity mapping](NAMING_MAP.md) and [historical validation evidence](evaluation/provenance/integration-validation.json). Validate the bundle with python -m backend.catalog.

## Authoring and acceptance

The single authoring source is the [OCCT benchmark construction and acceptance guide](../../docs/benchmark-authoring.md). It includes the end-to-end author workflow, Agent patch acceptance criteria, manifest structure, current suite counts, and portable validation commands. The [catalog format section of the main authoring guide](../../docs/benchmark-authoring.md#清单格式与目录结构) is the authoring reference; the schemas remain the exact field contract.

## Single-issue expansion of 2026-11-03

The twenty `occt-single20-*` tasks add 80 required checkpoints. All 160 frozen B/F executions completed. The defective original case fails on each B baseline, and every required F checkpoint passes. Calibration also rejects 61 reference-side negative controls.

The [qualification report](../../CADAI/tmp/kernel_bench_web_report/occt_single20_authoring_20261103.md) records task identities, geometric predicates, reference limitations, and evidence. The [machine-readable matrix](../../research/occt-single20-authoring-20261102/qualification-matrix.json) links each result to its preserved log. M33639 uses a verified older working commit as its geometric positive reference.

Use `scripts/prepare_single20_source.py` to reconstruct the new locked baselines from existing upstream Git objects. Derived baselines include their inverse source patch and exact Git commit object in `evaluation/provenance/single20/`.

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
