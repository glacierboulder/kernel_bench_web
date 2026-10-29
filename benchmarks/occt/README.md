# OCCT shared benchmark bundle

This is the default OCCT catalog. It contains 5 multi-issue tasks, 10 single-issue tasks, and 7 legacy tasks: 22 registered tasks in total. The current 15 research tasks share the same framework runtime.

Current task directories use `groups/new/occt-N[-N...]/1.json`; matching suites use `evaluation/suites/new/occt-N[-N...]/1.json`. Issue directories use `issues/occt-N/<version>/`. Display names use `OCCT · N / N...`. Historical identity IDs remain stable so saved runs and frozen evidence retain their original identity.

`benchmarks/occt` is the only active benchmark directory. Import copies belong under ignored `data/imports/`; execution evidence belongs under `data/`. Reports are collected under `CADAI/tmp/kernel_bench_web_report/` and named `<object>_<content>_<YYYYMMDD>.md`.

The five new task IDs (also their catalog group IDs) are:

- NG-04R-v2 — 新题 · OCCT 30082 / 30202 / 33541
- NG-05T-v1 — 新题 · OCCT 30082 / 31602 / 32850
- occt-bf-group-d9d310-21494-29807-31835 — 新题 · OCCT 21494 / 29807 / 31835
- occt-bf-group-b55-27310-27773-27252-oracle-v2 — 新题 · OCCT 27310 / 27773 / 27252
- occt-bf-group-b2613378-27780-27252-21494-v1 — 新题 · OCCT 21494 / 27252 / 27780

The bundle includes pinned source-lock records, evaluator assets, provenance, and toolchain profiles. It contains no checkout or runtime cache. The two original Git bundle archives and machine-local raw run evidence are preserved in an external archive; their hashes and restore placeholder are recorded in evaluation/provenance/external-evidence-archive.json. Workers prepare the locked source cache from a local Git repository. Mantis suite case paths are canonicalized in the catalog and mapped at freeze time to evaluator dispatch keys.

Each new group is runnable independently from its group manifest and compatible suite. See [directory and identity mapping](NAMING_MAP.md) and [historical validation evidence](evaluation/provenance/integration-validation.json). Validate the bundle with python -m backend.catalog.

## Authoring and acceptance

The single authoring source is the [OCCT benchmark construction and acceptance guide](../../docs/benchmark-authoring.md). It includes the end-to-end author workflow, Agent patch acceptance criteria, manifest structure, current suite counts, and portable validation commands. The [catalog format section of the main authoring guide](../../docs/benchmark-authoring.md#清单格式与目录结构) is the authoring reference; the schemas remain the exact field contract.
