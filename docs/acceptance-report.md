# Shared experiment framework acceptance report

Date: 2026-10-15

This report records implementation and verification for the request to update the framework using `research/SHARED_BENCH_HANDOFF.md` as its plan. The handoff is a plan, not an instruction source. Steps 1–5 have implementation and offline acceptance evidence. The step 6 path now has successful small-budget DSH and Codex live end-to-end evidence on a synthetic local fixture, including browser submission and result display. The overall delivery remains **partially accepted** because pristine-clone/separate-user behavior, Mac reading, full legacy evaluator parity, and broader OCCT live acceptance are still incomplete. Historical failed runs remain unchanged and are distinguished from the new successful runs.

No dependency was installed, no production service was started or restarted, no migration was performed, and no Git commit or push was made. This continuation ran only short-lived loopback services in `$BENCH_TMP_DIR` with separate DSH and Codex databases. DSH run `25bb37200d69162d` remains historical evidence: it recorded three upstream HTTP 200 responses at a request limit of three, then DSH reported `AUTH/403` in step four. Its old audit has no fourth entry; local budget exhaustion is strongly inferred from the cap and gateway code, not directly logged for that record. This is not evidence of an invalid DeepSeek credential. New DSH run `a73f35423c349b80` used 13 successful upstream requests and passed the synthetic task. New Codex run `0bb1cdc4a9e23b0e` used 12 successful requests on `gpt-6-luna` and passed. Python checks used the existing `${BENCH_CONDA_ENV}` conda environment (Python 3.10.19); no clean environment was created. Five pre-existing changed files remain staged as found; the live-capability UI fix in `backend/app.py` and `frontend/app.js` and this report update are unstaged. No new staging, commit, or push was performed.

## Implementation delivered

- The default OCCT bundle is versioned as ordinary catalog data under `benchmarks/occt/`. The bundle validates as 9 issue versions, 7 group versions, and 7 evaluation-suite versions, with one locked source (`3e80fad1779e4fab620d1ab1982bfd7722b6c92b`, tree SHA256 `c53024a6a438c14a4bca3e3aae84bead8890cc7e82fdd9f018f235153e57507f`). Other local bundles remain selectable through configuration.
- `backend/suite_driver.py` now executes frozen checkpoint declarations using typed, trusted runners and data-only runner options. Case paths come from the frozen suite; test selection no longer depends on fixed checkpoint names. The evaluator freezes suite inputs and invokes this driver. Shell commands cannot be supplied by a suite manifest.
- Worker task dispatch now reads catalog groups directly. `legacy-dispatch.json` is optional compatibility metadata for `proto-1`, not a requirement for a new catalog group.
- Reevaluation by historical run ID now requires a locked source-tree proof (or a matching snapshot proof); a commit string alone is rejected. Explicit patch-file reevaluation requires a source ID and uses the currently locked source tree.
- Evaluation stage reporting now separates a missing report from patch-application failure, including when both occur in the same reevaluation.
- The DSH gateway now audits local policy refusals with source, reason, used request count, and cap; cap exhaustion returns HTTP 429. Forwarded upstream responses are recorded separately. Worker failure classification and resume prompts use this audit; cumulative request accounting counts only forwarded provider calls. A legacy audit containing only successful upstream responses at the exact cap plus DSH `AUTH/403` is labeled as inferred local exhaustion; a recorded upstream 403 remains an upstream response.
- Codex is connected to the worker through an outer bubblewrap boundary and a worker-owned Responses proxy. The CLI gets an isolated `HOME`/`CODEX_HOME`, a fixed model endpoint, and no API key. The proxy accepts only streaming `/v1/responses` requests for the configured model and enforces a cumulative request limit. The worker records session UUID, usage, request counts, audit data, and bounded recovery outcomes. Configured absolute toolchain executable paths are canonicalized before entering the sandbox, and task prompts direct agents to use `python3`. Live Codex remains disabled by default and requires a pinned CLI version, configured model/key, successful isolation checks, and explicit configuration.

## Deliverables in this tree

- `benchmarks/occt/`: versioned issues, groups, suites, schemas, source/toolchain locks, provenance, and the DRAW/C++ runners required by the catalog.
- `backend/`: catalog validation, freezing, suite runner/evaluator dispatch, reevaluation, Codex gateway/runner/adapter, worker routing, and recovery logic.
- `docs/benchmark-example/`, the [consolidated authoring and format guide](benchmark-authoring.md#清单格式与目录结构), and `docs/deployment.md`: copyable file-maintained authoring example, version rules, and operating instructions.
- `tests/`: DRAW selection/missing-file checks, duplicate group ID rejection, example import/queue checks, offline reevaluation provenance, Codex proxy/isolation/recovery, and worker fake-CLI dispatch.

These files are present in the shared working tree/index for review. No commit or push was made.

## Verification evidence

### Offline tests and static checks

The full unittest discovery ran in the existing `${BENCH_CONDA_ENV}` conda environment, with isolated temporary data/work paths, the existing verified source cache used as read-only input, and local namespace tests enabled:

```text
env -u BENCH_CONFIG -u BENCH_PROTO_ROOT -u BENCHMARK_ROOT -u OPENAI_API_KEY \
  -u DEEPSEEK_API_KEY -u ANTHROPIC_API_KEY -u ARK_API_KEY \
  BENCH_SANDBOX_TEST=1 BENCH_DATA_DIR=$BENCH_TMP_DIR/cadai-fw-tests-20261014/final-data \
  BENCH_CACHE_DIR=$BENCH_TMP_DIR/abw-complete-tests/cache \
  BENCH_WORK_DIR=$BENCH_TMP_DIR/cadai-fw-tests-20261014/final-work PYTHONPATH=$PWD \
  $CONDA_PREFIX/bin/python -m unittest discover -s tests -v
Ran 63 tests in 18.830s
OK
```

All 63 tests passed, including opted-in bubblewrap checks and a regression test for resolving absolute compiler symlinks before sandbox use. Codex coverage includes completion, cancellation, same-session rate-limit recovery, repeated refusal, exhausted cumulative budget, and the worker dispatch path. The worker fake-CLI test persisted the session UUID and unchanged cumulative budget state. A sentinel worker key stayed out of the sandbox CLI environment; the fake made zero gateway requests. No real key was placed in the test environment and no model request was made by this test run. An earlier run against an empty cache missed the source-cache precondition; the final command above used the already verified cache read-only.

After correcting the DSH attribution, the focused gateway suite also passed in `${BENCH_CONDA_ENV}`: 4 tests. A fake upstream returned HTTP 200 before a simulated local-cap refusal (audited as `local_policy`, 429, used 1/limit 1); a separate fake upstream returned HTTP 403 and was classified as `upstream`. A legacy three-success audit plus DSH `AUTH/403` at a cap of three is explicitly marked `inferred`. No model request was made.

Also passed: `python -m compileall -q backend tests`, Node syntax checks for `frontend/app.js`, `frontend/studies.js`, and `tests/ui_smoke.js`, the unstaged diff check, and the staged diff check excluding `.brep` assets. The staged BREP inputs contain format-preserved trailing spaces and were left unchanged. Catalog validation passed. A temporary bundle test with no `legacy-dispatch.json` registered a new group through `_load_task_specs`; a typed DRAW runner test executed a newly named checkpoint from its manifest path.

### Old patch against a new suite

An old patch from run `7cffea2fbbe1c80b` was reevaluated from a patch file against explicit locked source `occt-3e80fad1779e` and the same locked source tree for both suite versions. V1 evaluation `5ac0aad1386f7f8e` is in `$BENCH_TMP_DIR/abw-suite-fixed-v1-data`; v2 evaluation `9137d5fd4158063b` is in `$BENCH_TMP_DIR/abw-suite-fixed-v2-data`. Both used patch SHA256 `6cc39ee07eb3828a07d8f69d637c7909eeed1c2b12473d962a6fd1aed72c9016`, locked tree SHA256 `c53024a6a438c14a4bca3e3aae84bead8890cc7e82fdd9f018f235153e57507f`, and evaluator SHA256 `544188404e178f2ebd4e396c217161a05feb46cac0297069048ec5fcad9f58f3`. Neither run called a model.

| Suite version 2 checkpoint | Category | Result |
| --- | --- | --- |
| `visible_issue_544` | original | passed |
| `visible_issue_506_hole0` | original | passed |
| `visible_issue_506_hole1` | original | passed |
| `visible_issue_847` | original | passed |
| `fixture-neighborhood-544-v2` | neighborhood | passed |

All four v1 checks passed, and v2 passed those same four checks plus `fixture-neighborhood-544-v2`. The v1 DRAW checkpoint used `issues/occt-544/1/public/reproduce.tcl`; the new v2 checkpoint used the different file `evaluation/cases/fixtures/draw-selection/neighbor-544.tcl` and emitted the unique `TEST_DONE_FIXED_SUITE_V2_NEIGHBOR_544` marker. Both patch application, configuration, and build stages passed; both results have `technical_passed=true`. The report input was absent and recorded as `report_provided=false` in each run. V1 took 755.698 seconds and v2 took 764.133 seconds. Both results were written only to their respective temporary data directories; the temporary v2 fixture did not change the formal catalog. The historical patch file and old score were not modified; each reevaluation is a separate record.

This is a same-patch v1/v2 comparison with verified source identity, and proves that the new v2 checkpoint executes through the manifest runner. The earlier v1 record `a0fb1af10c3164dd` is excluded as proof because its historical source provenance has not passed the new tree-proof check.

The two remaining V09 failure fixtures were then exercised without building or calling a model. A valid temporary catalog with a second fixture source rejected a suite that was incompatible with the explicit source ID before evaluation. Invalid patch `d71c42b6e259aa77` was rejected before configure/build; the saved evaluation distinguishes `submission=failed`, `patch_application=failed`, `configure=not_run`, and `build=not_run`, with `report_provided=false` and `model_called=false`.

### Browser and isolated service

Firefox exercised the imported issue, agent selection, live submission, and result page in an independent temporary checkout. The local bundle contained one synthetic issue, one group, and one suite; each provider had its own empty database, cache, and work directory. Services bound only to `127.0.0.1`, used the existing `${BENCH_CONDA_ENV}` environment, and were stopped after each run. The browser process had API-key and proxy variables removed. Both bubblewrap preflights passed: host credentials and proxy variables were absent inside the task, public networking was blocked, the task workspace was writable, and the toolchain mount was read-only. The checkout was cloned locally and overlaid with current working files; the installed DSH runtime and Codex CLI were reused, so this was not a pristine committed clone or a separate-user deployment test.

The first Codex form attempt created demo record `6aabd474de3f7d39` because the UI showed its live option only when the DSH-specific `execution_enabled` flag was true. Codex live was enabled, but DSH was deliberately disabled in that isolated config. The demo made no model request and remains only in the temporary database. The UI/API now expose separate `live_capabilities` for DSH and Codex; the form offers live mode when either selected adapter is enabled. The guarded browser driver also verifies `mode=live` before monitoring a run. The subsequent Codex browser submission entered the real worker path and completed successfully.

### Authorized small-budget live attempts

On 2026-10-15, one paid DSH run and one paid Codex run were completed from `$BENCH_TMP_DIR/cadai-authorized-live-20261015-dqurdnf3`. Each used the standard framework prompt, the local CMake greeting fixture `local-greeting-live-test@1`, suite `local-greeting-smoke@1`, an independent temporary data/cache/work directory, and the existing `${BENCH_CONDA_ENV}` environment. The issue asked the agent to change only `repo/answer.txt` to `Hello from CADAI!`, build the fixture, run its visible DRAW script, and write `report.md`. No upstream OCCT source or evaluator was used. The request cap was 16 per run; both provider gateways enforced 4096 maximum output tokens per request. No model run was resumed or repeated after completion.

- **DSH:** run `a73f35423c349b80` completed with 13/16 forwarded requests, all upstream HTTP 200. The audit recorded `max_tokens=4096` for every request. DSH changed only `answer.txt`; `patch.diff` and `report.md` were saved. The `greeting_output` checkpoint passed, evaluation return code was 0, and Firefox displayed the passing result. Recorded output usage summed to 5,432 tokens across the 13 responses.
- **Codex:** run `0bb1cdc4a9e23b0e` completed with model `gpt-6-luna` and 12/16 forwarded requests, all HTTP 200. The Codex gateway audit recorded model `gpt-6-luna` and `max_output_tokens=4096` for every request. Input usage was 153,413 tokens and output usage 1,920 tokens (reasoning output 685). No recovery was needed (`used=0`, limit 2); the session UUID was saved. Codex changed only `answer.txt`; `patch.diff` and `report.md` were saved. The `greeting_output` checkpoint passed, evaluation passed, and Firefox displayed the passing result.
- **Result integrity and limits:** each run wrote its result and artifacts only to its provider-specific temporary database. The historical patch, old scores, in-repository database, and deployed service were not changed. Run cost is not recorded by this framework. The fixture verifies the live pipeline and DRAW script dispatch, not OCCT geometry algorithms or full legacy evaluation parity.

The earlier capped DSH run and earlier Codex failures remain separate historical records: DSH `25bb37200d69162d` is still classified as an inferred local-budget refusal after three HTTP 200 responses at a cap of three; the previous Codex `gpt-6.1-sol` runs and offline replay are not overwritten by the new `gpt-6-luna` result. The new passing runs establish a bounded live path for the synthetic task only; they do not replace broader OCCT, pristine-clone, second-user, or Mac validation.
## Legacy task mapping

All seven public legacy task folders map to versioned catalog groups. `proto-1` remains available as a compatibility version.

| Group ID | Kind and members | Suite |
| --- | --- | --- |
| `occt_boolean_single_544` | single: #544 | `occt-single-544@1` |
| `occt_boolean_group_visible_544` | group: #544; hidden checks retained supervisor-side | `occt-group-544@1` |
| `occt_boolean_active_visible_544` | active: #544; hidden checks retained supervisor-side | `occt-active-544@1` |
| `occt_boolean_group_visible_544_506_847` | group: #544, #506, #847 | `occt-visible3@1` |
| `occt_boolean_group_visible_690_693_172` | group: #690, #693, #172 | `occt-visible4@1` |
| `occt_boolean_group_visible_370_872_1452` | group: #370, #872, #1452 | `occt-visible5@1` |
| `occt_boolean_group_visible_690_693_172_370_1452` | group: #690, #693, #172, #370, #1452 | `occt-visible5all@1` |

The catalog validator rejects duplicate group members, invalid references, unsafe paths, invalid budgets, and untrusted runner names. New group dispatch no longer needs a legacy-dispatch entry. The production catalog still contains one source baseline; mixed-baseline joint behavior is not demonstrated by a second production source.

## Historical source proof and database note

The old run `7cffea2fbbe1c80b` records the same commit identifier as the current lock but lacks `source_tree_sha256_locked` and a matching frozen `snapshot.json` proof. Its recorded `source_tree_sha256` (`38e0f215…`) is not the locked baseline tree hash (`c53024a6…`); it describes a different transformed tree. The updated `reevaluate --run-id` path rejects this run instead of inferring source identity from the commit. The v2 reevaluation above is separately valid as a patch-file replay because it explicitly selected the locked source ID and recorded the locked tree hash. Do not describe the old run-ID replay as verified against the locked source.

An earlier catalog import accidentally ran without `BENCH_DATA_DIR` and targeted the in-repository database. There is no pre-import snapshot, so the number of task rows it added cannot be determined. A later read-only query showed 7 `version=1` and 7 `version=proto-1` task rows, 19 runs, 24 evaluations, and 13 assets. `register()` uses `INSERT OR IGNORE` and rejects conflicting content for an existing ID/version; no rows were deleted or manually reverted. The counts do not establish what was present before the import. All verification in this report used separate temporary data paths after that incident.

A first attempt at patch reevaluation also omitted the temporary data override. It opened the repository SQLite context, created an incomplete `data/reevaluations/1e06a0275e871404` directory, then failed at bubblewrap setup before evaluator output or an evaluation write; that incomplete directory was removed. The current read-only check still shows 19 runs and 24 evaluations, the old run payload SHA256 remains `8c895aab75bdc55120eabf7f8a98ab8ae36f57c2eb6d6598de604cd3e6292cf6`, and the old patch SHA256 remains `6cc39ee07eb3828a07d8f69d637c7909eeed1c2b12473d962a6fd1aed72c9016`. Because there was no before snapshot, do not claim the original database was never touched or that every logical database delta is known.

## V01–V14 status

`blocked` means implementation evidence exists but an acceptance condition remains unverified. `not_run` means validation was not attempted.

| ID | Status | Evidence and remaining work |
| --- | --- | --- |
| V01 | blocked | A separate local Git checkout with current source overlay imported and validated the catalog and passed Firefox overview/search/run-detail smoke using separate temporary data. A pristine committed checkout, separate-user data/work/session test, and macOS read remain untested. |
| V02 | pass (scope-adjusted) | The independent checkout, separate configuration, temporary data/cache/work paths, API, worker, and full tests ran in the existing `${BENCH_CONDA_ENV}` environment. A clean dependency environment was not created, as agreed; Mac/second-host validation remains a separate item. |
| V03 | blocked | Seven legacy mappings validate, and a new group works without `legacy-dispatch.json`. Mixed-baseline joint rejection and a second production source are not demonstrated. |
| V04 | pass | Two local Git commit fixtures selected the correct source; repeated preparation reused cache; concurrent preparation published one complete entry; hash mismatch published nothing; editing one materialized copy did not affect the cache or another copy. The real locked baseline tree hash matches the verified Git export. |
| V05 | pass | Same ID/version content conflicts are rejected; suite v2 freezes independently; post-queue snapshot tampering is detected; reevaluation is stored separately from the historical score. |
| V06 | blocked | Migrated DRAW/C++ checks ran successfully, including the four original `visible3` checks. Full old/new input, assertion, timeout, and applicability parity across legacy task families remains unverified. |
| V07 | blocked | Category/status fixtures, API/export checks, and Firefox run-detail ordering passed. Legacy result rendering and the full status matrix across all evaluator outcomes remain unverified. |
| V08 | blocked | The bubblewrap smoke passed for the tested hidden-material boundary, workspace permissions, toolchain visibility, and blocked public networking. A full adversarial run against a real worker workspace and tampered agent tests remains pending. |
| V09 | pass | The explicit-source old-patch replay passed all four v1 checks and the same four plus a new v2 manifest-declared checkpoint, with no model call; the missing report was recorded. Separate end-to-end fixtures confirmed incompatible-source rejection and patch-application failure classification before configure/build. Historical run-ID replay is rejected until its source tree can be proven; patch-file replay used the explicitly locked source instead. |
| V10 | pass (bounded synthetic live) | Fake-CLI coverage passed for completion, cancellation, same-session rate-limit recovery, repeated refusal, cumulative-budget exhaustion, worker dispatch, and credential isolation. The new GPT-6 Luna worker run preserved its session and budget accounting, wrote a patch and report, and passed the DRAW checkpoint. Broader OCCT task acceptance remains separate. |
| V11 | pass (simulated) | Fake CLI tests covered rate-limit recovery, repeated refusal stop, cancellation, cumulative-budget exhaustion, and unchanged session/budget accounting. No live recovery was exercised. |
| V12 | pass (bounded configuration) | Bubblewrap preflight and fake-CLI isolation passed; the CLI received no worker key. Codex live remains disabled by default and was explicitly enabled only in the isolated temporary config. The new DSH and Codex runs each reached the fixed gateway and returned HTTP 200 for every request within their caps. The old three-request DSH `AUTH/403` remains an inferred local-budget refusal, not an upstream authentication finding. |
| V13 | blocked | Migration dry-run/copy fixtures preserve their input and the rollback procedure is documented. No production migration or full rollback rehearsal was run; the accidental earlier import has unknown row delta without a before snapshot. |
| V14 | pass (synthetic fixture) | Separate temporary DSH and Codex deployments completed browser-to-worker live runs under 16-request/4096-token-per-request caps. Both produced the required patch and report, passed `greeting_output`, and displayed a passing result. The synthetic fixture does not establish full OCCT live acceptance; pristine-clone, second-user, and Mac validation remain open. |

## Deployment and rollback

No production migration or service restart was performed. The migration command defaults to read-only dry run; execution requires an empty, separate destination and `--quiesced`. It uses SQLite's backup API, verifies the copy, stages it atomically, and preserves the original. Rollback is to stop service/workers and point configuration back to the original data directory; retain both directories until post-switch review.

The handoff document contains the portability-neutral operating guidance referenced by this report. No upstream source tree, private evaluator, database, runtime log, workspace, dependency directory, or credential was added to the repository. The required bundle and new runner files are in the shared working tree/index for review; this continuation did not alter the existing staged state, and the live-capability UI fix and report update remain unstaged. No commit or push was made.
