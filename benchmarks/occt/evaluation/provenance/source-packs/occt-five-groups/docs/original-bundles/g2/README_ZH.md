# OCCT B/F 第二组 staging：M27310 / M27773 / M27252

这是已通过 Sol 最终审阅并登记的第二个独立 Part2 bundle，计入新增正式组目标的 **2/4**。组和 suite 身份均为 `occt-bf-group-b55-27310-27773-27252-oracle-v2` / `occt-bf-suite-b55-27310-27773-27252-oracle-v2`。审阅依据见[最终审阅记录](../../planning/reviews/BF_GROUP2_FINAL_ACCEPTANCE_ZH.md)和[正式登记记录](../../validation/bf_group2_delivery/FORMAL_REGISTRATION_ZH.md)。Agent 仍只交 `patch.diff` 与 `report.md`；B 是被测源码，F 只在 supervisor sidecar 中表达校准来源，不要求作者联合 reference patch，也不接受空 patch 冒充参考修复。

下面命令先设置使用者本机路径。runner 的期望环境名从部署配置读取，不要求固定环境名称：

```bash
export BF2_BUNDLE=/path/to/occt-bf-group2
export BF2_GROUP=occt-bf-group-b55-27310-27773-27252-oracle-v2
export BF2_EVIDENCE="${OCCT_RAW_EVIDENCE_ROOT:?restore historical evidence from the external archive}/$BF2_GROUP"
: "${BF2_CONDA_ENV:=${BENCH_CONDA_ENV:?set a configured Conda environment name}}"
```

## 源码身份与恢复

两个源码身份来自官方 Git 仓库 <https://github.com/Open-Cascade-SAS/OCCT.git>：

| 角色 | 完整 commit | Git tree | materialized tree SHA-256 |
|---|---|---|---|
| B | `b55bd02353519ebba14575f8056bb2b14585089e` | `4f7bb9c62242b211d7edcd98e8792a158fc8dddf` | `b65869dfa1367bb32a63e47accc1552de0fa6a6d5bd8a90a38db64bd4c7aaa77` |
| F | `e6afb53983172155891ef175943534e0e1a24f75` | `c4eef2db9b5c2873b4b287346a8142bb97280e1b` | `a28f641dad6310bece14379db895a7da1482305273ccffd5ebb3b8774d03e841` |

Bundle 不复制完整 Git 库，也不绑定某个用户目录。在有本地 OCCT worktree 的机器上，先确认两个完整 commit 对象存在、tree 身份匹配且 B 是 F 的严格祖先：

```bash
export BF2_REPO=/path/to/local/OCCT
git clone --no-checkout https://github.com/Open-Cascade-SAS/OCCT.git "$BF2_REPO"
git -C "$BF2_REPO" cat-file -e 'b55bd02353519ebba14575f8056bb2b14585089e^{commit}'
git -C "$BF2_REPO" cat-file -e 'e6afb53983172155891ef175943534e0e1a24f75^{commit}'
test "$(git -C "$BF2_REPO" rev-parse 'b55bd02353519ebba14575f8056bb2b14585089e^{tree}')" = 4f7bb9c62242b211d7edcd98e8792a158fc8dddf
test "$(git -C "$BF2_REPO" rev-parse 'e6afb53983172155891ef175943534e0e1a24f75^{tree}')" = c4eef2db9b5c2873b4b287346a8142bb97280e1b
git -C "$BF2_REPO" merge-base --is-ancestor b55bd02353519ebba14575f8056bb2b14585089e e6afb53983172155891ef175943534e0e1a24f75
```

若本地对象库不含这些对象，可从上游 URL 克隆或补取包含这两个 commit 的官方 refs，再运行上述检查。B/F 的 materialized tree SHA-256 由下方锁定 validator 通过 `git archive` 重算；普通 `git rev-parse` 不能代替该检查。恢复和验证只需一个同时含两 commit 的本地 worktree，不需要把它打进 bundle。

## 独立数据目录的导入与冻结

复用兼容框架的正式命令时，给每次验收一个新的数据、cache、work 目录，并将 `BENCHMARK_ROOT` 指向该 bundle。`agent-bench-web` 是外部只读框架 checkout；下例不访问现有部署数据：

```bash
export BF2_FRAMEWORK=/path/to/agent-bench-web
export BF2_SCRATCH="$(mktemp -d)"
export BENCHMARK_ROOT="$BF2_BUNDLE"
export BENCH_DATA_DIR="$BF2_SCRATCH/data"
export BENCH_CACHE_DIR="$BF2_SCRATCH/cache"
export BENCH_WORK_DIR="$BF2_SCRATCH/work"
export PYTHONPATH="$BF2_FRAMEWORK${PYTHONPATH:+:$PYTHONPATH}"
unset BENCH_PROTO_ROOT
mkdir -p "$BENCH_DATA_DIR" "$BENCH_CACHE_DIR" "$BENCH_WORK_DIR"
cd "$BF2_FRAMEWORK"
conda run --no-capture-output -n "$BF2_CONDA_ENV" python -m backend.import_proto
conda run --no-capture-output -n "$BF2_CONDA_ENV" python -m backend.source_cache \
  occt-b55bd0235351 --from-dir "$BF2_REPO"
```

接着可通过框架的冻结 API 生成独立快照并验证其内容；source-cache 必须先成功：

```bash
conda run --no-capture-output -n "$BF2_CONDA_ENV" python - <<'PY'
import os
from pathlib import Path
from backend.catalog import public_task, validate_bundle
from backend.freeze import freeze_catalog_task, materialize_source, verify_snapshot

bundle = validate_bundle(Path(os.environ["BENCHMARK_ROOT"]))
group = bundle["groups"][("occt-bf-group-b55-27310-27773-27252-oracle-v2", "1")]
task = public_task(bundle, group)
run_root = Path(os.environ["BENCH_WORK_DIR"]) / "freeze"
run_root.mkdir(parents=True)
manifest = freeze_catalog_task(task, run_root)
snapshot = run_root / "benchmark-snapshot"
verified = verify_snapshot(snapshot)
materialize_source(snapshot, run_root / "materialized-B")
print({"snapshot_sha256": verified["snapshot_sha256"],
       "materialized_B_tree_sha256": manifest["source_tree_sha256"]})
PY
```

以上是可移植复跑路径；本次实际隔离导入、source-cache、freeze、snapshot verification 与 replays 的逐项证据在仓库内的 delivery report 中。

## 使用冻结随包 runner 重放

快照中的 runner 位于 `supervisor/legacy/scripts/run_draw_case.py`；它会从同目录加载锁定的 `run_eval.py`。二进制、`env.sh` 和资源目录不随 bundle 复制，需在运行主机提供先前验证且 hash 符合 sidecar build identities 的本地 B/F 构建产物。以下示例一条重放公开 B 原例，一条重放隐藏 F 邻域；两者都直接调用冻结快照内的 runner：

```bash
export BF2_SNAPSHOT=/path/to/frozen/benchmark-snapshot
export BF2_RUNNER="$BF2_SNAPSHOT/supervisor/legacy/scripts/run_draw_case.py"
export BF2_PUBLIC_DIR="$BF2_SNAPSHOT/supervisor/cases/bundle/issues/occt-27310/1/public"
export BF2_HIDDEN_DIR="$BF2_SNAPSHOT/supervisor/evaluator_tests/$BF2_GROUP"
export BF2_EVIDENCE="$BF2_BUNDLE/evaluation/provenance/bf/$BF2_GROUP"
export BF2_LOG_DIR="$(mktemp -d)"
export BF2_B_BUILD=/path/to/verified/B-build-root
export BF2_B_RESOURCES=/path/to/B-source/src
export BF2_F_BUILD=/path/to/verified/F-build-root
export BF2_F_RESOURCES=/path/to/F-source/src

# Public M27310_1 on B: completed geometry_fail is the expected outcome.
conda run --no-capture-output -n "$BF2_CONDA_ENV" env \
  BENCH_REQUIRED_CONDA_ENV="$BF2_CONDA_ENV" python "$BF2_RUNNER" \
  --role B --build-dir "$BF2_B_BUILD" --resource-dir "$BF2_B_RESOURCES" \
  --case-dir "$BF2_PUBLIC_DIR" --script harness_bug27310_1.tcl \
  --log "$BF2_LOG_DIR/B_M27310_1.log" \
  --source-commit b55bd02353519ebba14575f8056bb2b14585089e \
  --materialized-tree b65869dfa1367bb32a63e47accc1552de0fa6a6d5bd8a90a38db64bd4c7aaa77 \
  --build-record "$BF2_EVIDENCE/build-configs/B/build_baseline_gcc_o0_test_plugin.json" \
  --timeout-seconds 180 --cpu-limit-seconds 160 --address-space-gib 4

# Hidden M27310 finite-face neighborhood on F: completed geometry_pass is expected.
conda run --no-capture-output -n "$BF2_CONDA_ENV" env \
  BENCH_REQUIRED_CONDA_ENV="$BF2_CONDA_ENV" python "$BF2_RUNNER" \
  --role F --build-dir "$BF2_F_BUILD" --resource-dir "$BF2_F_RESOURCES" \
  --case-dir "$BF2_HIDDEN_DIR" --script M27310_neighbor_finite_face.tcl \
  --log "$BF2_LOG_DIR/F_M27310_neighbor_finite_face.log" \
  --source-commit e6afb53983172155891ef175943534e0e1a24f75 \
  --materialized-tree a28f641dad6310bece14379db895a7da1482305273ccffd5ebb3b8774d03e841 \
  --build-record "$BF2_EVIDENCE/build-configs/F/build_e6afb_gcc_o0_test_plugin.json" \
  --timeout-seconds 180 --cpu-limit-seconds 160 --address-space-gib 4
```

若设置 `BENCH_REQUIRED_CONDA_ENV`，它必须与当前 `CONDA_DEFAULT_ENV` 一致；否则 runner 只要求 `CONDA_PREFIX` 指向一个有效的 Conda 环境。runner JSON 的 `execution.status` / `oracle.status` 是结果；B 的 geometry_fail 会使命令返回 1，sidecar 映射将它归为已完成的 oracle 运行，不能只看 shell 返回码。对完整矩阵按 suite manifest 中的 checkpoint case/role 组合重复调用即可。

## Sidecar 与可移植验证

私有记录在 `evaluation/provenance/bf/occt-bf-group-b55-27310-27773-27252-oracle-v2/`。其中 `bf_evidence.json` 锁 3 个 canonical 成员、10 个 case、17 条 B/F 执行记录、输入、oracle、runner、build 配置及原始日志 hash；`acceptance.json` 锁 sidecar SHA-256 `718655021fbfbdf1d12ec88d2938b1ebfcab71d2636baef388c75d8fe004e281` 和可信 runner。Acceptance 字节 SHA-256 为 `483f87c67dda01d3484a17837fb4b5929074ca69a337c0c8c192d429ee201fe2`；当前 runner SHA-256 为 `9ebd9f0a67bb31c6ecec5cac0fbd0cff5f0384b4749aad7b2f83626887923c76`。公开 `sources.lock.json` 仍只锁 B，不放入 F 身份。

验证器位于 `tools/supervisor/validate_bf_evidence.py`，格式说明和工具自身 hash 位于同目录。它将 sidecar 中 `sources.B.repository` / `sources.F.repository` 的相对路径从 **manifest 所在目录** 解析；当前锁定值是 `repo`，不是 bundle 根目录。保持 sidecar 和 acceptance 原字节不变，在本机临时副本中创建运行时 `repo` 符号链接：

```bash
export BF2_GROUP=occt-bf-group-b55-27310-27773-27252-oracle-v2
export BF2_EVIDENCE="$BF2_BUNDLE/evaluation/provenance/bf/$BF2_GROUP"
export BF2_RUNTIME="$(mktemp -d)"
mkdir -p "$BF2_RUNTIME/evidence"
cp -a "$BF2_EVIDENCE"/. "$BF2_RUNTIME/evidence/"
ln -s "$BF2_REPO" "$BF2_RUNTIME/evidence/repo"
conda run --no-capture-output -n "$BF2_CONDA_ENV" python \
  "$BF2_BUNDLE/tools/supervisor/validate_bf_evidence.py" \
  --manifest "$BF2_RUNTIME/evidence/bf_evidence.json" \
  --acceptance-manifest "$BF2_RUNTIME/evidence/acceptance.json"
```

CLI 成功只表示记录、Git 身份、文件 hash、runner lock 和矩阵结构通过；它自身不重跑几何，也不能证明 oracle 或 runner 的真实性。需要把实际 runner 代码和输出一起审阅。该组的既有执行配置锁为 GCC 9.4、`-O0 -DNDEBUG`、j1、DRAWEXE/TKTopTest 和外部 xlocale overlay hash；build config SHA-256 为 `b2e05826db2049cb53f5ba99739251ff4c7c943ca7915251622f2be826b65810`。这里报告复用此前已验证的构建产物，不表示本 bundle 做过 fresh build 或第二台机器复建。

## 集成与几何验证证据

隔离导入、B source-cache、冻结快照与冻结路径重放的复现入口在对应工作区的 `validation/bf_group2_delivery/run_snapshot_replay.py`。它接收 `--repo <local OCCT worktree>`，使用独立 runtime/data/cache/work 路径，并在验证目录写报告和逐次运行记录。历史集成实测结果曾记录在 `validation/bf_group2_delivery/`；这些生成记录不属于公开 Agent 输入。

本阶段结果为 17/17 completed 且与预期一致：4 个 official original 均为 B 几何失败、F 通过；3 个 hidden neighborhood 的 F 通过；3 个 hidden regression 的 B/F 均通过。M27310 使用官方 d308 原例版本，原先关闭的旧 R1 结论不被覆盖。M27310 finite-face neighborhood 的几何预期是一条下支**开弧**，含解析端点约束；不是闭弧。M27310 regression 要求两物理闭合组件，采样满足两柱方程、分支符号相反，端点连接图闭合且正负 x 各一；原始输出 4 段和 seam 坐标只作为表示观察，不是几何正确性门槛。

冻结快照 SHA-256 为 `2d9c17313c1d43d83ade3d1ce2349bfcd3d62cf7c203e514f0ea8eb9dd11dbdd`，B source-cache 显示 `verified_git`，materialized B hash 匹配锁。冻结后 17 条重放仍为 4 fail / 13 pass；公开文件 20 个，hidden case 文件 6 个，hidden case 名称/ID 与 F commit 泄漏检查均通过。canonical member 与 Part1、已验收第一组及禁用 issue 无重合；与静态候选表的交集仅是候选规划记录，已单独披露，不是 catalog 任务。矩阵 SHA-256 为 `7df14bc3bad1e1b107483918d1d2dc1e3de3ee933828708a21dc7bf0938aa887`。

Sidecar validator 输出 `formal_acceptance: requires_human_review`、`geometry_replayed: false`、`oracle_authenticity_proven: false`；实际冻结重放由上述独立 replay 报告证明。上述验证字段不替代已通过的 Sol 最终审阅；本目录是正式 catalog 之外单独选择的独立 bundle，不与第一组的不同 evaluator 合并。
