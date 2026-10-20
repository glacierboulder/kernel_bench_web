# Plan 1B experiment protocol

This protocol follows `occt-boolean-branching-proposal-zh.md` and the simplified first-pilot plan. It tests whether Plan 1A repair knowledge helps an agent discover and validate additional issues on one shared repaired kernel.

## Frozen inputs and comparison

Each first-pilot Plan 1B batch freezes one verified K1, its B0 regression manifest, one M0 asset from the same K1, the agent configuration, prompt/schema versions, evaluator fingerprint, and per-run budget. The first pilot has exactly two independent runs without M0 and two with M0. Both arms use identical K1, B0, module/runtime instructions, model, time/request limits, and tools. Only the with-M0 input bundle contains `M0/knowledge.json`. Runs do not share workspaces, sessions, findings, patches, or hidden feedback. The default per-request output cap is 8192 tokens and can be set before service startup with `BENCH_PLAN1B_MAX_OUTPUT_TOKENS`; each batch freezes its value. A run allows at most one `max_tokens` continuation through DSH headless `--session-id`; it reuses the same session and workspace and shares the original request and wall-clock budgets. If the limit is reached again, valid partial output is preserved and the run is marked incomplete.

The current protocol supports open exploration. A controlled blind cohort requires a separately registered hidden target pack that remains outside the agent input bundle; it is not enabled until that private target lifecycle exists. Open exploration with no confirmed finding is recorded as inconclusive for discovery ability, not as a failure.

K1 must have status `verified`, an intact source-tree hash, and a combination evaluation. M0 must be an `evidence_linked` or `verified` knowledge asset whose `kernel_id` is that exact K1. B0 freezes the known public issue suites from the K1 source runs, the analytic Boolean regression fingerprint, and the visible-suite evaluator fingerprint. It does not claim full upstream OCCT coverage.

## Agent input package

The per-run ZIP contains:

- `execution_protocol.json`: run/arm/repeat IDs, K1 and B0 hashes, agent config, and frozen budgets.
- `B0/manifest.json`: known suites, public source-run references, regression/evaluator hashes, and scope.
- `agent_prompt.md`: Plan 1B task instructions and output requirements.
- `output-schema.json`: machine-readable candidate and knowledge field definitions.
- `M0/knowledge.json`: present only for the with-M0 arm.

The dedicated `backend.plan1b_worker` mounts a fresh copy of the verified K1 source tree as each agent's writable workspace and exposes the frozen public B0 tooling. It never passes private evaluator inputs, blind targets, reference patches, or hidden score feedback. The downloadable protocol ZIP omits the approximately 220 MiB K1 tree because the trusted worker mounts the frozen asset directly. The worker uses the existing bubblewrap boundary and fixed DeepSeek API gateway, and waits until the established Plan 1A/parallel workers are idle before claiming a Plan 1B run. It does not share sessions or workspaces across repeats.

## Required output package

The agent returns one ZIP rooted directly at these paths:

- Required `exploration_report.md`: search scope, risk hypotheses, commands/tools, results, limitations, and actual budget use.
- Required `findings.jsonl`: one JSON object per candidate; an empty file means no candidates.
- `generators/`: generator or mutation scripts.
- `cases/`: serialized inputs and any metadata needed to replay them.
- Optional `patch.diff`: one unified patch based on the frozen K1.
- Optional `new_tests/`: proposed regression tests and replay instructions.
- Optional `knowledge_candidates.json`: JSON array of proposed knowledge with explicit evidence references and limits.
- Optional `run-metadata.json`: elapsed time, request/token use, continuation count, completion status, cost, model, and runtime version when available.
- Optional `agent.jsonl`: execution trace.

Each `findings.jsonl` record has these required fields. `knownness` and `known_issue_reference` are optional agent claims; the independent reviewer separately freezes the platform classification so new issues remain distinguishable from neighborhoods of known issues.

```json
{
  "candidate_id": "candidate-001",
  "k1_sha256": "<frozen K1 source tree SHA256>",
  "input_path": "cases/candidate-001.brep",
  "input_sha256": "<SHA256 of the exact input file>",
  "generator_path": "generators/search.py",
  "generator_sha256": "<SHA256 of the exact generator file>",
  "seed": 17,
  "parameters": {"tolerance": 1e-7},
  "repro_command": "python generators/replay.py cases/candidate-001.brep",
  "expected": "...",
  "actual": "...",
  "oracle": "...",
  "applicability": "...",
  "knownness": "new_issue",
  "known_issue_reference": ""
}
```

`knowledge_candidates.json` is an array. Each entry requires `candidate_id`, `claim`, `evidence_candidate_ids`, `scope`, and `limitations`. Evidence references must name candidate IDs from the same run.

The importer rejects path traversal, symlinks, special files, oversized archives, unlisted top-level paths, missing reports/schema files, wrong K1 hashes, absent candidate files, or mismatched file hashes. Contract failures remain attached to the run and cannot be independently confirmed or promoted.

## Independent confirmation and scoring

An independent reviewer records input-contract validity, three deterministic replay results on clean K1, oracle violation, root-cause deduplication, novelty (`new_issue`, `known_issue_neighborhood`, or `unknown`), and evidence. A known-neighborhood classification must cite the related known issue/root cause. A candidate is confirmed only when the contract passes, all three replays pass, the oracle confirms a violation, and the finding is not a duplicate. Agent assertions alone do not count.

If a patch was attempted, the review also records whether it applies to clean K1 and whether the new case, neighborhood, and all B0 tests pass. Confirmed findings can enter B1. A patch that passes the recorded repair criteria is retained as a K2 candidate for separate platform-side combination verification. Evidence-linked knowledge candidates can enter M1; knowledge remains a claim with stated scope and limitations.

The records retain arm, repeat, run IDs, artifact hashes, request/token/cost metadata, confirmed findings, repair outcomes, and promoted assets so the two arms can be compared without conflating discovery with repair.

## Web/API lifecycle

1. Create a batch from the verified K1, matching M0, DSH agent, repeat count, request limit, and wall-clock budget.
2. Download one frozen input protocol per prepared run; upload the corresponding output ZIP once.
3. Review each candidate and freeze its independent evaluation record.
4. Select confirmed findings to create a B1 archive. Findings with a successful patch review may also create a K2 candidate; evidence-backed knowledge entries create M1.

API resources: `POST /api/explorations`, `GET /api/explorations/{id}`, `GET /api/explorations/{id}/runs/{run_id}/input`, `POST /api/explorations/{id}/runs/{run_id}/submission`, `PUT /api/findings/{id}/review`, and `POST /api/explorations/{id}/promote`.
