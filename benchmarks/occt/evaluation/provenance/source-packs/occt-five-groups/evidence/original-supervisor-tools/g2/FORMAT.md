# 私有 B/F 证据 sidecar 格式 v1

本目录中的 sidecar 和验证器只供监督校准及交付审查使用。它不修改公开 suite schema、freeze、Agent 可见输入或 Agent 的 `patch.diff + report.md` 契约。sidecar 最终交付时，必须由外层交付 acceptance manifest 固定 sidecar 文件的 SHA-256；现有 source locks 不承载 F 身份。

验证器检查 Git 对象、归档源码树、输入/oracle/runner/build-config 文件、结构化执行记录和原始日志的真实字节。它为 Git archive hash 在系统临时目录创建并清理短期副本，不改写仓库或证据文件；它不构建源码、不下载资产。工具能证明这些本地材料与记录的 hash 和身份字段相符，不能单凭 sidecar 证明运行者诚实、OCCT oracle 正确或几何结果真实。交付审查者必须先批准可信 runner 的代码身份，再把 runner ID/hash 写入 acceptance manifest 的 `trusted_runners`。工具不会重放几何测试，也不会把本目录的 tiny Git 测试 fixture 当成 OCCT 实测。

## 顶层字段

| 字段 | 含义 |
|---|---|
| `format_version` | 固定为 `1`。 |
| `example_only` | 示例模板为 `true`；验证器会拒绝它。真实 sidecar 必须是 `false`。 |
| `mode` | `candidate_originals` 或 `formal`。模式写在 sidecar 中，CLI 不允许降级。 |
| `candidate_id` | 私有候选组标识。 |
| `members` | canonical 成员列表，每项包含公开 suite 可映射的 `issue_id`/`issue_version` 与稳定 `canonical_id`。 |
| `build_config` | 实际构建配置文件的相对路径和 SHA-256。 |
| `sources.B`, `sources.F` | Git 仓库路径、完整 commit、Git tree object SHA-1/SHA-256，以及框架 materialized tree hash。仓库路径相对 sidecar 目录或绝对路径；它只用于本机只读核验。 |
| `cases` | 用现有 suite `case_id`、`issue_id` 和 `issue_version` 表示的输入/语义 oracle/runner 身份。每个文件均在 sidecar 目录内，以相对路径引用并单独校验 SHA-256。Runner 声明 `process_exit_mapping`，明确将每个进程退出码映射到执行状态。 |
| `runs` | 每个 source/case 的执行记录路径、SHA-256 与原始 stdout/stderr 日志路径、SHA-256。执行记录必须重复 source/case/hash 身份，且日志 SHA 必须与记录一致。 |

输入可以由多个文件组成。`inputs_sha256` 是对按 UTF-8 路径字节排序的列表 `[{"path": ..., "sha256": ...}]` 做 UTF-8、JSON `ensure_ascii=false`、`sort_keys=true`、紧凑分隔符序列化后再 SHA-256 的摘要。case 的 oracle 声明 `check_ids`；执行记录必须给出完全相同的唯一 check ID 集合和布尔 `passed`。`oracle.status` 必须由这些 checks 推导：全部通过为 `geometry_pass`，任一失败为 `geometry_fail`。

`execution_record` 是 runner 产出的 JSON，至少包含以下字段；其完整文件本身也由 sidecar run 行锁 SHA-256。`execution.status` 只能是 `completed`、`not_run`、`timeout`、`runtime_error`。只有 `completed` 且 `oracle_ran=true` 才进入几何结果判断；其 `process_return_code` 必须由 case runner 的 `process_exit_mapping` 映射为 `completed`。非零返回码可以有效，例如几何测试驱动用非零码表达测试失败，但该映射必须同时写进 sidecar 与 acceptance manifest 的可信 runner 锁。`signal` 和 `timeout_seconds` 在适用时记录；非 completed 状态必须使用 `oracle.status=not_run` 和空 checks，且永远不能计为几何 pass/fail。

```json
{
  "format_version": 1,
  "source": "B",
  "case_id": "suite-case-id",
  "canonical_id": "mantis:30001",
  "issue_id": "mantis-30001",
  "issue_version": "4",
  "category": "original",
  "source_commit": "<full-commit-hex>",
  "source_tree_sha256": "<64-hex-sha256>",
  "inputs_sha256": "<64-hex-sha256>",
  "oracle_sha256": "<64-hex-sha256>",
  "runner_sha256": "<64-hex-sha256>",
  "runner_process_exit_mapping": {"0": "completed", "1": "completed"},
  "build_config_sha256": "<64-hex-sha256>",
  "log_sha256": "<64-hex-sha256>",
  "build": {"status": "passed", "return_code": 0},
  "execution": {
    "status": "completed",
    "oracle_ran": true,
    "process_return_code": 1,
    "signal": null,
    "timeout_seconds": null
  },
  "oracle": {
    "status": "geometry_fail",
    "checks": [{"id": "predicate-id-from-oracle", "passed": false}]
  }
}
```

执行记录中的 build 状态必须为 `passed` 且 build return code 为 `0` 才能产生几何结论。Runner 的进程返回码与 build 返回码分开：前者只按锁定的 `process_exit_mapping` 判定执行是否完成，几何分类来自已运行 oracle 的结构化 checks。`not_run`、`timeout`、`runtime_error`、缺输入、oracle 未复现等都不能作为 B 的几何失败。

## 矩阵规则

- `candidate_originals`：只允许 `original` case；每个 canonical member 至少一个 original case；每个 original 必须各有一条 B 和 F 记录。B 必须为 `geometry_fail`，F 必须为 `geometry_pass`。验证成功只表示“候选原例证据格式和身份完整”，CLI 会明确标记 `formal_acceptance=false`。
- `formal`：必须有 3–5 个不同 canonical member；每个 member 至少有 original、hidden `neighborhood` 和 hidden `regression` case。original 必须在 B/F 都有记录（B 几何失败、F 通过）；neighborhood 必须在 F 有记录且通过；regression 必须在 B/F 都有记录且通过。缺任一类别、记录、成员、锁或身份校验均失败。`candidate_originals` 可用单 member 探索。
- 不允许重复 `(source, case_id)`。本版本只要求最小矩阵：不接受未定义的额外 source/category 组合。
- B 和 F 必须是同一 Git repository 中不同的完整 commit，且 B 是 F 的严格祖先。验证器同时核对 `commit^{tree}` 和基于 `git archive <commit>` 的 materialized tree SHA-256。materialized hash 排除项与当前 source cache 一致（`.git`、`__pycache__`、`CMakeFiles`、任意 `build` 路径组件、`.pyc`、`.pyo`）。

## Acceptance lock

Formal CLI 必须通过 `--acceptance-manifest` 指向外层交付 acceptance manifest。其最小结构为：

```json
{
  "bf_evidence": {
    "path": "bf_evidence.json",
    "sha256": "<sidecar 文件字节的 SHA-256>",
    "trusted_runners": [
      {
        "id": "approved-runner-v1",
        "sha256": "<runner 文件 SHA-256>",
        "process_exit_mapping": {"0": "completed", "1": "completed"}
      }
    ]
  }
}
```

`path` 相对 acceptance manifest 目录，必须指向 CLI 正在验证的同一个 sidecar。Formal 验证要求每个 case runner 的 ID/hash/`process_exit_mapping` 都与该锁一致。候选模式可在尚未交付锁时运行，但报告 `acceptance_lock_verified=false`。Acceptance manifest 的批准过程以及 runner 的真实性判断是人工决策；hash 和映射锁不能单独证明 runner 实际执行了所声称的工作。

## CLI

```text
python validate_bf_evidence.py --manifest <private-sidecar.json> [--acceptance-manifest <delivery-acceptance.json>]
```

退出码 `0` 表示所声明模式下的证据结构和身份检查通过；退出码 `2` 表示拒绝。JSON 报告会把 `geometry_replayed=false` 与格式/身份验证结果分开呈现。运行检查必须使用已有 `${BENCH_CONDA_ENV}` 环境。

公开 suite 到 sidecar 的最小映射是：suite 的 `case_id` 原样写入 `case_id`，`issue_id`/`issue_version` 原样映射，监督层另给稳定 `canonical_id`；若现有来源无法唯一映射，先由 Sol 定义映射，不在此工具中猜测或扩展公开 schema。
