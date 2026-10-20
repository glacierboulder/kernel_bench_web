# 第一新增自然 B/F 组：已验收 bundle 与可移植复现说明

本目录是已通过 Sol 最终审阅并登记的 Part2 bundle，包含 3 个 issue、1 个 group、1 个 suite 和 12 个 case。本组是新增正式组 4 组目标中的第 1 组（1/4）。审阅结论见[最终审阅记录](../../planning/reviews/BF_GROUP1_FINAL_ACCEPTANCE_ZH.md)；交付与机器证据见[交付报告](../../validation/bf_group1_delivery/DELIVERY_REPORT_ZH.md)、[sidecar 校验](../../validation/bf_group1_delivery/formal_sidecar_validation.json)、[B/F 矩阵](../../validation/bf_group1_delivery/matrix_final_v3/bf_matrix.jsonl)和[snapshot freeze 边界](../../validation/bf_group1_delivery/snapshot_replay/final_freeze_verification.json)。

## 本机路径与隔离数据

使用者自行提供框架 checkout、bundle 根目录以及现有 OCCT Git checkout 的路径。目录约定只通过环境变量传入，不依赖作者机器上的绝对路径。命令使用已存在且依赖等价的 conda 环境；环境名称由部署配置提供。本文不要求安装依赖。

```bash
export BUNDLE_ROOT=/path/to/occt-bf-part2
export FRAMEWORK_ROOT=/path/to/agent_bench_web
export OCCT_CHECKOUT=/path/to/existing/OCCT-git-checkout
export BENCHMARK_ROOT="$BUNDLE_ROOT"
: "${BENCH_CONDA_ENV:?set this to a configured Conda environment name}"
unset BENCH_PROTO_ROOT

export BENCH_RUN_ROOT="$(mktemp -d "${TMPDIR:-$BENCH_TMP_DIR}/occt-bf-group1.XXXXXX")"
export BENCH_DATA_DIR="$BENCH_RUN_ROOT/data"
export BENCH_CACHE_DIR="$BENCH_RUN_ROOT/cache"
export BENCH_WORK_DIR="$BENCH_RUN_ROOT/work"
mkdir -p "$BENCH_DATA_DIR" "$BENCH_CACHE_DIR" "$BENCH_WORK_DIR"
```

`BUNDLE_ROOT` 必须直接指向含 `catalog.json` 的目录。临时 data/cache/work 保持彼此隔离，也不要指向框架正在使用的数据库或缓存。

## B/F 源码身份

同一个本地 Git 对象库必须同时含有 B 和 F 两个 commit。不要用没有 `.git` 对象库的源码导出替代它；若本地 checkout 缺少任一对象，本说明不要求联网补取。

| 版本 | commit | Git tree object | 框架 materialized tree SHA-256 |
|---|---|---|---|
| B | `d9d3107d8df19cacc3d7a0cd46ba51deee0bf6f2` | `e49aed8e43873abeb4dbfc84048b2956f51da268` | `fdc06c2924af2315e740cec852552d1f9b8d8def2dd13f8a3f592b289885403f` |
| F | `870ae593c3c060fe822e20bd2f1acfdd3fcbd449` | `75920cb58780f31d7063633b98095dfb69821abe` | `8f57dd653c66586b33e5cdd60dbae743b921c07c860358904dfa99f45ebf9857` |

Git tree object 是 Git 的 40 位对象标识；materialized hash 是框架对 `git archive` 展开后源码内容计算的 64 位 SHA-256。两者不能互相替代。公开 `sources.lock.json` 固定 B；私有 B/F sidecar 固定两侧。验证时检查完整 commit、tree object、同一仓库及 `B` 为 `F` 的严格祖先：

```bash
B_COMMIT=d9d3107d8df19cacc3d7a0cd46ba51deee0bf6f2
F_COMMIT=870ae593c3c060fe822e20bd2f1acfdd3fcbd449
git -C "$OCCT_CHECKOUT" cat-file -e "${B_COMMIT}^{commit}"
git -C "$OCCT_CHECKOUT" cat-file -e "${F_COMMIT}^{commit}"
test "$(git -C "$OCCT_CHECKOUT" rev-parse "${B_COMMIT}^{tree}")" = e49aed8e43873abeb4dbfc84048b2956f51da268
test "$(git -C "$OCCT_CHECKOUT" rev-parse "${F_COMMIT}^{tree}")" = 75920cb58780f31d7063633b98095dfb69821abe
git -C "$OCCT_CHECKOUT" merge-base --is-ancestor "$B_COMMIT" "$F_COMMIT"
```

validator 会用本地 Git archive 重算 materialized SHA-256，并比较以上锁值。`backend.source_cache` 只需准备公开 B source；它读取本地 checkout，不需要联网：

```bash
cd "$FRAMEWORK_ROOT"
conda run -n "$BENCH_CONDA_ENV" python -m backend.source_cache occt-d9d3107d8df1 --from-dir "$OCCT_CHECKOUT"
```

## 随包侧车验证与 `repository: "repo"`

私有证据中的 `sources.B.repository` 和 `sources.F.repository` 都是相对 sidecar 目录的路径 `repo`。验证时将 sidecar 文件复制到临时目录，再把本机 Git checkout 以 `repo` 名称临时链接进去；验证器从该链接读取 Git objects 并调用 `git archive`。这样无需复制整份 Git 仓库、改写 sidecar 或访问 bundle 外的作者路径。

```bash
SIDECAR="$BUNDLE_ROOT/evaluation/provenance/bf/occt-bf-group-d9d310-21494-29807-31835"
VERIFY_DIR="$(mktemp -d "${TMPDIR:-$BENCH_TMP_DIR}/occt-bf-verify.XXXXXX")"
cp -a "$SIDECAR/." "$VERIFY_DIR/"
ln -s "$OCCT_CHECKOUT" "$VERIFY_DIR/repo"

# 在复制的临时目录验证已审阅工具及其格式说明的锁。
conda run --no-capture-output -n "$BENCH_CONDA_ENV" python - "$BUNDLE_ROOT" <<'PY'
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1])
lock = json.loads((root / "tools/supervisor/SUPERVISOR_TOOL_LOCKS.json").read_text())
for item in lock["files"]:
    path = root / item["path"]
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != item["sha256"]:
        raise SystemExit(f"hash mismatch: {item['path']}")
print(f"verified {len(lock['files'])} locked supervisor files")
PY

conda run -n "$BENCH_CONDA_ENV" python "$BUNDLE_ROOT/tools/supervisor/validate_bf_evidence.py" \
  --manifest "$VERIFY_DIR/bf_evidence.json" \
  --acceptance-manifest "$VERIFY_DIR/acceptance.json"
```

验证器的退出码 0 表示 sidecar 声明的 Git 身份、文件 hash、矩阵结构和 acceptance lock 一致。它不构建源码、不运行几何 case，也不单独证明 oracle 正确；这些边界见随包的 [FORMAT.md](tools/supervisor/FORMAT.md)。验证脚本与格式说明的 SHA-256 由 [SUPERVISOR_TOOL_LOCKS.json](tools/supervisor/SUPERVISOR_TOOL_LOCKS.json) 固定。

## catalog、导入与 freeze

在框架 checkout 根目录、临时 `BENCH_DATA_DIR` 下检查 bundle 并导入公开题目：

```bash
cd "$FRAMEWORK_ROOT"
conda run -n "$BENCH_CONDA_ENV" python -m backend.catalog --json
conda run -n "$BENCH_CONDA_ENV" python -m backend.import_proto
```

导入会写 SQLite，因此只对上述新建的临时 data 目录执行。下面直接调用框架只读 bundle API 生成本地 freeze probe，不排队 Agent，也不调用模型：

```bash
GROUP_ID=occt-bf-group-d9d310-21494-29807-31835
export GROUP_ID
conda run --no-capture-output -n "$BENCH_CONDA_ENV" python - <<'PY'
import json, os
from pathlib import Path
from backend.catalog import public_task, validate_bundle
from backend.freeze import freeze_catalog_task, materialize_source, verify_snapshot
from backend.settings import SETTINGS

bundle = validate_bundle(SETTINGS.benchmark_root)
group = bundle["groups"][(os.environ["GROUP_ID"], "1")]
root = SETTINGS.data_dir / "freeze-probe" / group["id"]
snapshot = root / "benchmark-snapshot"
manifest = freeze_catalog_task(public_task(bundle, group), root)
verify_snapshot(snapshot)
materialized = materialize_source(snapshot, root / "materialized-B")
print(json.dumps({"snapshot": manifest, "materialized_B": str(materialized)}, indent=2))
PY
```

检查 snapshot manifest 指向 B commit/tree，并确认物化 B 与 source lock 的 materialized SHA-256 一致。freeze 只准备任务材料；它不会执行 B/F 几何验证。

## 已记录的 snapshot replay 与复跑命令

本组实际 snapshot-path replay 使用了已经构建并 hash 验真的 B/F `DRAWEXE`，由冻结 snapshot 中的 `supervisor/legacy/scripts/run_draw_case.py` 调用。结果包括：M21494 原例 B 几何失败、F 通过；M21494 邻域及 M29807 邻域在 F 通过；另保留了一次因 `--resource-dir` 指错而未加载 TOPTEST plugin 的 `not_run` 尝试。B/F `DRAWEXE` SHA-256 分别为 `0e78f47dcec578cf0b67eba46277710e618a91bd4ac48af4acca6eae13f81b71` 和 `bc9406526b1c4c2a032c3f332f8bf8a1ba7d22614cdeaa5a09df870bb3dbd779`。

这些几何 replay 使用的 snapshot SHA-256 是 `f9f4bd922369b855717f53d8b057320d2d84756745c5ca414772af5a75d26417`。之后生成的最终 freeze SHA-256 是 `7061389057da282e6c33ccbe7db8659ab9534163bd3517e252a001b387b57c14`；两者之间仅 `tools/build.sh` 与 snapshot manifest 有变化，公开/隐藏 case 和输入资产身份未变。几何 replay 没有在最终 snapshot 上重跑。

如需在自己的 freeze probe 上复跑已覆盖的 case，先将变量指向与 B/F commit 对应的**现有、已验证** build 和源码目录；`*_SOURCE_TREE` 的 `src` 子目录必须含对应版本的 `DrawResources`。以下只调用现有二进制，不会执行 build helper：

```bash
GROUP_ID=occt-bf-group-d9d310-21494-29807-31835
SNAPSHOT="$BENCH_DATA_DIR/freeze-probe/$GROUP_ID/benchmark-snapshot"
export BENCH_TOOLCHAIN_NAME=clang
export LIBGL_ALWAYS_SOFTWARE=1
unset DISPLAY

# 例：B 的公开 M21494 原例
conda run -n "$BENCH_CONDA_ENV" python "$SNAPSHOT/supervisor/legacy/scripts/run_draw_case.py" \
  --build-dir "$B_BUILD_DIR" --resource-dir "$B_SOURCE_TREE/src" \
  --case-dir "$SNAPSHOT/supervisor/cases/bundle/issues/occt-21494/1/public" \
  --script harness_bug21494_2.tcl

# 例：F 的 M21494 隐藏邻域
conda run -n "$BENCH_CONDA_ENV" python "$SNAPSHOT/supervisor/legacy/scripts/run_draw_case.py" \
  --build-dir "$F_BUILD_DIR" --resource-dir "$F_SOURCE_TREE/src" \
  --case-dir "$SNAPSHOT/supervisor/cases/bundle/evaluation/cases/evaluator_tests/$GROUP_ID" \
  --script M21494_neighbor_sphere9p5.tcl
```

检查 runner JSON 内的 `test_done_marker`、`BF_CASE_ORACLE`/专用几何 marker 和 DRAW 诊断；`run_draw_case.py` 自身退出 0 不能单独作为几何通过。上述示例不重放整个 21 项 B/F 矩阵。

## 构建证据边界

本组矩阵和 snapshot replay 复用了已有 Clang 10、`-O0 -DNDEBUG`、`j1` B/F 构建。bundle 中的 `tools/occt-clang10-bf-d9-v1/build.sh` 和 legacy `run_eval.py` 没有作为 fresh build/helper replay 执行；最终 freeze 核验也记录 `build_shell_executed=false`、`fresh_build_replay=false`。本组已通过 Sol 最终审阅并登记；干净构建复现、第二台机器复现和未来 Agent 修复回放仍未验证。
