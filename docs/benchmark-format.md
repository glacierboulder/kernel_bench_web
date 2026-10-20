# Benchmark catalog format

The OCCT bundle is self-contained except for its pinned upstream source cache. `catalog.json` indexes versioned public issues, groups and suites. `backend.catalog` validates it using Python's standard library, so catalog reading does not import web or Linux-only modules.

```text
benchmarks/occt/
  catalog.json
  sources.lock.json
  issues/occt-<number>/<version>/{issue.json,statement.md,public/*}
  groups/new/occt-<ordered-numbers>/<version>.json
  groups/legacy/occt-<mode>-<ordered-numbers>/<version>.json
  evaluation/suites/{new,legacy}/<ordered-name>/<version>.json
  evaluation/cases/                 # trusted supervisor-only materials
  evaluation/provenance/            # supervisor provenance
  tools/<tools-directory>/          # reviewed task tools
  toolchains/<profile-id>.json
```

## Source lock and tree hash

Each source entry has a unique `source_id`, upstream URL, full 40-character commit, materialized tree SHA256, verification status, provenance reference and toolchain profile. The cache importer exports a commit from a local Git object database. It does not clone, fetch or otherwise use the network.

`agent-bench-tree-sha256-v1` sorts relative POSIX paths by UTF-8 byte order. For each non-directory path it hashes the relative name, NUL separators, file type (`F` regular file or `L` symlink), executable-bit flag, byte length, payload and a final NUL. Regular-file payload is the complete file content; symlink payload is its relative link text, and links escaping the root are rejected. `.git`, `__pycache__`, `CMakeFiles`, any `build` path component and `.pyc` / `.pyo` files are excluded.

An existing non-Git export is not described as an upstream checkout. It can only be imported with the explicit unverified option and must still match the locked tree hash. Cache publication uses a per-source lock and atomic directory rename. Published cache files are read-only; each run gets an independent writable copy.

## Issue versions

`issue.json` has `schema_version`, `id`, `version`, `title`, `source_id`, a relative `statement` path and a non-empty `public_materials` list. All paths are POSIX relative paths and may not escape the issue directory or traverse symlinks. Public issue materials are limited to bounded regular files. A source commit or public statement/input change requires a new issue version.

Each issue version maps to exactly one baseline. To add a source at another commit, add a new source lock entry and new issue versions. Do not point one issue version at alternative baselines.

## Group versions

A group has `schema_version`, `id`, `version`, `title`, `kind`, `source_id`, `execution_mode`, unique issue/version members, a group-scoped wall budget, required outputs and an explicit evaluation suite reference. `kind` is `single`, `group` or `active`; `execution_mode` is `joint` or `independent`. A joint group cannot mix source IDs. Active-task `findings.jsonl` is a format deliverable; format validity does not score discovery quality.

The current registry permits `patch.diff`, `report.md` and `findings.jsonl` output names. Budgets are bounded and compiler jobs cannot exceed two. A group update uses a new **group ID**. A catalog may contain only one version for each group ID; validation fails if two rows use the same group ID, even when their version strings differ. This avoids the worker's ID-based dispatch silently replacing one version with another. To change members, execution mode, budget, output requirements, or the suite selected by a task, create a new group ID and keep the old entry for historical runs. If issue text or public inputs change, first publish a new issue version, then create a new group ID that references it. Import is idempotent for identical content and rejects a different payload under the same database ID/version.

## Evaluation suite versions

Suites are independently versioned. A suite declares compatible source IDs, compatible group IDs and checkpoint rows. Each checkpoint has a unique ID, optional issue ID, category (`original`, `neighborhood`, `regression`), visibility (`public`, `hidden`), trusted runner and oracle identifiers, a case file path relative to the bundle root, timeout and required flag. Registered runners are `draw_case_v1` and `cpp_case_v1`. For DRAW, `checkpoint.case` is the sole script-path field: its final filename is passed to the runner as `--script`; `runner_options.script` is rejected. `runner_options.case_timeout_seconds` may only shorten the checkpoint timeout. A missing `case` file is an error and cannot fall back to `reproduce.tcl`. C++ runner options contain only file inputs, approved OCCT library names, and output markers. Paths are resolved and symlinks rejected. The suite runner invokes no shell command from a manifest.

The current OCCT bundle migrates the existing DRAW and C++ checks; this work does not add formal OCCT checks. Adding or changing checks requires a new suite version and does not change prior run snapshots or results. A suite-only update can be selected explicitly when reevaluating an old patch. To make a new suite the default for newly queued tasks, create a new group ID that points to it. Catalog tasks dispatch directly from group and suite manifests. `legacy-dispatch.json` is optional compatibility metadata for old `proto-1` records, not a prerequisite for new tasks.

The default OCCT catalog currently contains five new three-issue groups and seven legacy groups. Directory names are normalized independently of stable catalog identities: issue IDs, group IDs, suite IDs, versions, source IDs, source commits, and locked source tree hashes remain unchanged. New group paths use `groups/new/occt-<ordered-numbers>/`; old groups use `groups/legacy/occt-<single|group|active>-<ordered-numbers>/`. Issue materials use `issues/occt-<number>/<version>/`. Suite manifests are under matching `evaluation/suites/new/` or `evaluation/suites/legacy/` paths. The full mapping and static evidence are recorded in [NAMING_MAP.md](../benchmarks/occt/NAMING_MAP.md).

Some Mantis suites retain evaluator dispatch keys that refer to their original `issues/mantis-<number>/...` paths. The generic freeze adapter resolves issue identity from catalog paths and records canonical-to-locked path aliases in `snapshot.json`; evaluator assets and dispatch locks remain byte-identical. A toolchain may set `evaluator_directory` to select an alternate trusted runtime; the default remains `evaluation/cases/legacy`.

Results distinguish `passed`, `failed`, `timeout`, `error`, `not_run` and `skipped`. Required checkpoints must pass for technical success. Empty categories report `未配置` and do not count as successful evidence. Hidden records remain on the supervisor side; public API output contains only a generic hidden-check summary.

## Validation and import

Validate the complete bundle without starting the web application:

```bash
python -m backend.catalog
```

Import public tasks into the currently configured SQLite database:

```bash
python -m backend.import_proto
```

Do not import into a live database solely for a fixture check. Use a dedicated `BENCH_DATA_DIR` for integration tests.
