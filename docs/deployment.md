# Deployment and runtime requirements

## Runtime layers

| Use | Requirements |
| --- | --- |
| Read and validate catalog | Python 3.9+ standard library; no Linux tools |
| Web application | Python 3.11, `requirements.txt` (FastAPI, Pydantic 2, Uvicorn) |
| Python tests | The web application environment plus Python `unittest` |
| Browser assets | Static HTML/CSS/JavaScript; Node is only needed for `node --check`; Firefox is optional for the rendered UI smoke |
| DSH runtime | Linux, Node, the pinned `runtime/dsh/package-lock.json`, bubblewrap user namespaces, Git, CMake, configured C/C++ compilers and Tcl 8.6 |
| Codex | A locally installed CLI can be probed, but Codex live remains disabled until CLI-version and credential-isolation checks pass |

Do not install OS packages globally. A fresh Python environment can be created from `environment.yml` after the operator approves its dependency installation. DSH npm packages are pinned; `npm ci` also installs dependencies and must be treated as an installation action. Doctor never installs anything.

## Configuration

`backend.settings` uses CLI > environment > JSON > defaults. Set `BENCH_CONFIG` to select a config file. Relative paths in the file resolve from that file's directory. Environment variables include:

| Variable | Purpose |
| --- | --- |
| `BENCHMARK_ROOT` | Primary catalog directory |
| `BENCH_PROTO_ROOT` | Legacy catalog alias, lower priority than `BENCHMARK_ROOT` |
| `BENCH_DATA_DIR`, `BENCH_CACHE_DIR`, `BENCH_WORK_DIR` | Account-local data, cache and work directories |
| `BENCH_PYTHON`, `BENCH_PYTHON_PREFIX`, `BENCH_CONDA`, `BENCH_CONDA_ENV` | Runtime selection |
| `BENCH_HOST`, `BENCH_PORT` | Web listener; keep it on loopback for SSH-tunnel use |
| `BENCH_GATEWAY_HOST`, `BENCH_GATEWAY_PORT` | Per-run loopback gateway endpoint |
| `BENCH_BWRAP`, `BENCH_CMAKE`, `BENCH_CC`, `BENCH_CXX` | Linux execution tools |
| `BENCH_TCL_DIR`, `BENCH_TCL_INCLUDE_DIR`, `BENCH_TCL_LIBRARY`, `BENCH_TCL_LIBRARY_DIR` | Toolchain Tcl locations |
| `BENCH_COMPILER_JOBS` | Compiler parallelism, capped at two |
| `BENCH_CODEX` | Codex executable probe only; it does not enable live runs |
| `http_proxy`, `https_proxy`, `no_proxy` | Standard network-client proxy variables |

Current task build tools and supervisor build helpers accept one or two compiler
jobs and default to two. Frozen run snapshots retain their original helpers;
after correcting runtime settings, use `backend.reevaluate` to create a new
evaluation of the saved patch rather than editing a historical snapshot.

The model gateway resolves proxy URL environment variables first, then the optional `proxies.http` and `proxies.https` config values. It does not print proxy URLs. Public-source preparation is local-only and makes no network request. Agent sandboxes receive no proxy variables or public network route.

`config.example.json` contains generic defaults. Never place API credentials in that file. DSH reads its key from the trusted worker environment; the sandbox receives only a placeholder while requests are relayed through the fixed model gateway.

## Start the service and SSH tunnel

Importing the catalog writes task rows to the configured database. Run it with a conda environment containing the Python dependencies:

```bash
conda activate <your-environment>
python -m backend.import_proto
python -m backend.doctor
./run.sh
```

For a service on a remote Linux host, leave the listener on loopback and create the tunnel from the client machine. Replace all shell variables with values from that deployment:

```bash
ssh -N -L "127.0.0.1:${LOCAL_PORT}:127.0.0.1:${BENCH_PORT}" "${REMOTE_USER}@${REMOTE_HOST}"
```

Open the local end of that tunnel in a browser. Do not bind the service to a campus or public interface unless the operator has separately configured access control and reviewed that exposure.

## Doctor and execution readiness

`python -m backend.doctor` is read-only. It reports package versions, catalog validity, source-cache hashes, configured executables, platform and whether Linux execution prerequisites appear present. A successful package check is not proof of sandbox isolation or successful OCCT compilation. `python -m backend.preflight` runs the actual bubblewrap boundary assertions; it creates and removes a temporary workspace but does not install or change host configuration.

The source cache is per account and immutable after publication. Prepare only a source requested by a task:

```bash
python -m backend.source_cache <source-id> --from-dir <local-git-checkout>
```

Catalog tasks are frozen into a run-specific snapshot at queue time. The verified source cache is copied and rechecked at worker start. Agent changes never modify the cache or another run.

To check the rendered overview, task list and task search against an already running service, set `BENCH_BROWSER_URL` (for example, the local end of an SSH tunnel) and run `python tests/browser_smoke.py`. Firefox must already be installed; `BENCH_BROWSER` can select its executable. The smoke does not start or restart the service.

## DSH, Codex and recovery

DSH uses the existing fixed CLI adapter and gateway. Live task creation requires a current worker and either a successful prior live verification or the operator's explicit `dsh_live_enabled: true` setting for a first bounded verification run. It defaults to false. Queueing a run may incur model charges after a worker claims it. Set `BENCH_CUMULATIVE_REQUEST_LIMIT` and `BENCH_MAX_OUTPUT_TOKENS` for a small trial before starting the worker; do not use `backend.worker --first` or submit live jobs without an explicit model and request budget.

Codex is connected to the worker through an outer bubblewrap boundary and a worker-owned Responses proxy. The CLI receives an isolated `HOME`/`CODEX_HOME`, a fixed model endpoint, and no API key; the proxy accepts only streaming `/v1/responses` requests for the configured model and enforces one cumulative request budget. The worker records the explicit session UUID, token usage, proxy audit, and bounded recovery decisions. Fake CLI tests cover completion, cancellation, rate-limit recovery, repeated refusal, exhausted budget, session continuity, and the worker dispatch path. A bubblewrap test confirms that a sentinel key stays out of the CLI environment and that the fake CLI makes no upstream request.

Live Codex remains disabled by default. Enablement requires an exact CLI version, a configured model and API key, successful credential-isolation checks, and explicit operator configuration (`codex_live_enabled` and `codex_isolation_verified`). The sample config sets both flags to false. A live run is a billable model call; use a dedicated data directory and a low cumulative request/output-token cap for acceptance.

The CLI uses Codex's documented non-interactive `exec` interface and the isolated `CODEX_HOME` environment variable ([Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode), [Codex environment variables](https://learn.chatgpt.com/docs/config-file/environment-variables)).

`backend.recovery.RecoveryBudget` is connected to the Codex worker path. It allows at most two outer resumes and at most one review-refusal continuation, waits for process exit, and requires an explicit session UUID. Unknown outcomes are inspected and stopped; authentication failures, safety refusals, cancellation, budget exhaustion and unknown errors stop. Fake CLI tests verify that a resume preserves the same session and that the cumulative request limit is not reset. No worker restart automatically spends more model budget.

## Offline reevaluation

Reevaluate a historical run by ID only when it ended in live mode and its recorded locked source-tree hash, or a matching frozen `snapshot.json`, proves the exact source tree against the current lock. A commit string alone is not sufficient. For older runs that lack that proof, extract the saved patch and explicitly select the source and suite:

```bash
python -m backend.reevaluate --patch $BENCH_TMP_DIR/old-run.patch \
  --source-id occt-3e80fad1779e \
  --suite-id occt-visible3 --suite-version 2
```

This path makes no model call, leaves the historical patch and score unchanged, and saves a new reevaluation record. An explicit source selection proves which current locked baseline was used; it does not retroactively prove that the old run used that baseline.

## Platform boundary

macOS and Windows can read or validate the JSON catalog without bubblewrap, a compiler, or a Linux filesystem. Executing OCCT tasks requires Linux and the configured sandbox/toolchain. An SSH tunnel connects a browser to that Linux service; it does not make local macOS execution available.
