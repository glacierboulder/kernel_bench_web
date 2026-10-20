# OCCT Part2 第三组正式 bundle：M27780 / M27252 / M21494

这是已通过 Sol 最终审阅并登记的第三个独立 Part2 bundle，计入新增正式组目标 **3/4**。Group/suite 身份为 `occt-bf-group-b2613378-27780-27252-21494-v1@1` / `occt-bf-suite-b2613378-27780-27252-21494-v1`；成员为 M27780@1、M27252@2、M21494@2。包含 3 个 issue、1 个 group、1 个 suite、9 个 case（3 个公开原例和 6 个隐藏 case）。审阅依据见[最终验收](../../planning/reviews/BF_GROUP3_FINAL_ACCEPTANCE_ZH.md)和[正式登记记录](../../validation/bf_group3_delivery/FORMAL_REGISTRATION_ZH.md)。原 staging 保留。Agent 只需提交 `patch.diff` 和 `report.md`；不要求联合 reference patch，也不接受空 patch 代替修复。

## 本机路径与 Conda 环境

下列变量由使用者按本机路径设置。命令只使用已安装环境和已有 OCCT checkout/build，不安装依赖、不联网：

```bash
export BF3_BUNDLE=/path/to/occt-bf-part2-group3
export BF3_GROUP=occt-bf-group-b2613378-27780-27252-21494-v1
export BF3_SNAPSHOT=/path/to/frozen/benchmark-snapshot
export BF3_REPO=/path/to/existing/OCCT-git-worktree
: "${BF3_CONDA_ENV:=${BENCH_CONDA_ENV:?set a configured Conda environment name}}"
export BF3_EVIDENCE="${OCCT_RAW_EVIDENCE_ROOT:?restore historical evidence from the external archive}/${BF3_GROUP}-agent-oracle-v4"
export BF3_OUT="$(mktemp -d "${TMPDIR:-$BENCH_TMP_DIR}/occt-bf-g3.XXXXXX")"
```

源码身份为 B `2613378e60ff5e517b2bf73699184d0c6f636bb8`（Git tree `43c6421991ea0372ec0f7622aa8daea5676a7b7e`）和 F `870ae593c3c060fe822e20bd2f1acfdd3fcbd449`（Git tree `75920cb58780f31d7063633b98095dfb69821abe`）。公开 source lock 只指向 B；F 身份保留在私有校准证据中。B/F 二进制应由使用者提供，并与 sidecar 中的 Clang 10、`-O0 -DNDEBUG`、`j1` build identity 相符；bundle 不含完整 OCCT 源码、build 或二进制。

## 冻结 runner 的直接调用

冻结快照中的 framework adapter 位于 `supervisor/legacy/scripts/run_draw_case.py`，会调用同一快照内锁定的几何 core 与 parser。下面以公开 M27780 原例的 agent 模式为例；实际结果写入 record/log。B 基线预期 `geometry_fail`、`test_done_marker=false`，命令退出码 1；F 参考预期通过、marker 为 true、退出码 0。agent 模式不把二进制 hash 当作校准身份门槛：它记录实际 artifact hash，并使用同一个几何 oracle。

```bash
export BF3_RUNNER="$BF3_SNAPSHOT/supervisor/legacy/scripts/run_draw_case.py"
export BF3_HELPER="$BF3_SNAPSHOT/supervisor/legacy/run_eval.py"
export BF3_PUBLIC="$BF3_SNAPSHOT/supervisor/cases/bundle/issues/occt-27780/1/public"
export BF3_B_BUILD=/path/to/existing/B-build-root
export BF3_B_RESOURCES=/path/to/B-source/src
export BF3_F_BUILD=/path/to/existing/F-build-root
export BF3_F_RESOURCES=/path/to/F-source/src

# B baseline: geometry_fail is a completed oracle result and returns 1.
set +e
conda run --no-capture-output -n "$BF3_CONDA_ENV" env \
  BENCH_REQUIRED_CONDA_ENV="$BF3_CONDA_ENV" python "$BF3_RUNNER" \
  --build-dir "$BF3_B_BUILD" --resource-dir "$BF3_B_RESOURCES" \
  --case-dir "$BF3_PUBLIC" --script harness_bug27780.tcl \
  --oracle-helper "$BF3_HELPER" --log "$BF3_OUT/B_M27780.log" \
  --record "$BF3_OUT/B_M27780.json"
rc=$?
set -e
test "$rc" -eq 1

# F reference: geometry_pass is a completed oracle result and returns 0.
conda run --no-capture-output -n "$BF3_CONDA_ENV" env \
  BENCH_REQUIRED_CONDA_ENV="$BF3_CONDA_ENV" python "$BF3_RUNNER" \
  --build-dir "$BF3_F_BUILD" --resource-dir "$BF3_F_RESOURCES" \
  --case-dir "$BF3_PUBLIC" --script harness_bug27780.tcl \
  --oracle-helper "$BF3_HELPER" --log "$BF3_OUT/F_M27780.log" \
  --record "$BF3_OUT/F_M27780.json"
```

Suite driver 使用同一 bundle-local `run_eval.py` wrapper：它导出 `apply_patch(source, patch_arg)`、`configure_and_build(source, build)` 和 `validate_draw_text(case_id, role, text, draw_return_code)`。wrapper 将几何谓词委托给锁定的 `geometry_oracle.py`，并从 `build_helper.py` 提供受控 Clang 10/O0/j1 build API；xlocale overlay 也单独锁定。实际 `_prepare_control` 布局已验证这些 API 的导入、签名、模块来源和私有资产路径。本轮未调用 patch/build API，也未 fresh-build。

The suite contains 3 public original cases, 3 F-only neighborhood checks, and 3 regression cases run on both B and F: 15 role executions total. The hidden scripts and numerical checks are supervisor-only. They parse values emitted by DRAW, then perform numeric geometry predicates in Python; command errors, parse errors, missing inputs, and generic runtime failures cannot count as geometry pass. Case-specific compatibility is limited to the reviewed pure-display adaptation and exact, documented tail diagnostics.

## Sidecar validator and tool lock

`tools/supervisor/SUPERVISOR_TOOL_LOCKS.json` pins the bundled `validate_bf_evidence.py` and `FORMAT.md`. The validator checks the B/F Git identities, input and run hashes, trusted runner, acceptance lock, and matrix structure; it does not rebuild OCCT or replay geometry. The sidecar expects a local Git worktree at relative path `repo`, so validate a temporary copy and leave the staged evidence unchanged:

```bash
export BF3_VERIFY="$(mktemp -d "${TMPDIR:-$BENCH_TMP_DIR}/occt-bf-g3-verify.XXXXXX")"
mkdir -p "$BF3_VERIFY/evidence"
cp -a "$BF3_EVIDENCE"/. "$BF3_VERIFY/evidence/"
ln -s "$BF3_REPO" "$BF3_VERIFY/evidence/repo"
conda run --no-capture-output -n "$BF3_CONDA_ENV" python \
  "$BF3_BUNDLE/tools/supervisor/validate_bf_evidence.py" \
  --manifest "$BF3_VERIFY/evidence/bf_evidence.json" \
  --acceptance-manifest "$BF3_VERIFY/evidence/acceptance.json"
```

Validator exit 0 means the evidence and its acceptance hash lock are structurally consistent; it is not a geometry replay or final acceptance. Review `evaluation/provenance/bf/$BF3_GROUP-agent-oracle-v4/acceptance.json` and the linked delivery reports alongside the validator output.

## 本轮边界

矩阵记录由 6 条已核验公开原例记录复用和 9 条更新后的隐藏角色实际运行组成。最终 staging 通过了当前字节的 isolated catalog import、B source-cache、freeze、snapshot verification、public leak/canonical overlap 检查及真实 `_prepare_control` 布局下的 suite-driver API 导入和公开 B/F 与隐藏 M21494 F smoke。未做 fresh build、未做第二台机器复跑，也未登记正式 catalog。
