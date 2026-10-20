# OCCT 五组独立 B/F 题库

此目录保留五组题库合并前的来源说明、映射及原始 supervisor 工具证据。当前可运行入口已迁至 `benchmarks/occt/`；目录格式和迁移结果见其 README、命名映射和验收记录。Part1/Part2 原目录不在本项目内；合并前文件的路径、catalog/source lock 摘要和 source bundle 哈希保留在本目录元数据与外部归档清单中。M21494@1/@2、M27252@1/@2 和 Mantis 30082@2/@4 按版本分别保留。

| Group | 成员 | Source ID | 固定 commit | Materialized tree SHA-256 | Toolchain |
|---|---|---|---|---|---|
| `NG-04R-v2@1` | M30082@2, M30202@2, M33541@2 | `occt-ng04r-derived-fe81a63b` | `75fad89c90cf0390a6a053fa43a290b3fbb05069` | `fe81a63b36e22d484a7ddcb49431c40d3d6e9febd2c5ce14631083c99a346c93` | Clang 10 |
| `NG-05T-v1@1` | M30082@4, M31602@2, M32850@1 | `occt-ng04t-v1-baseline-ef5af939` | `201a54e50b9f24ecd5d9c401461ad64312de9870` | `ef5af9392e97caa3a790cdea791453b51f88a3ef4305b47205354795363cf395` | Clang 10 |
| `occt-bf-group-d9d310-21494-29807-31835@1` | M21494@1, M29807@1, M31835@1 | `occt-d9d3107d8df1` | `d9d3107d8df19cacc3d7a0cd46ba51deee0bf6f2` | `fdc06c2924af2315e740cec852552d1f9b8d8def2dd13f8a3f592b289885403f` | Clang 10, `-O0`, j1 |
| `occt-bf-group-b55-27310-27773-27252-oracle-v2@1` | M27310@1, M27773@1, M27252@1 | `occt-b55bd0235351` | `b55bd02353519ebba14575f8056bb2b14585089e` | `b65869dfa1367bb32a63e47accc1552de0fa6a6d5bd8a90a38db64bd4c7aaa77` | GCC 9.4, `-O0`, j1 |
| `occt-bf-group-b2613378-27780-27252-21494-v1@1` | M27780@1, M27252@2, M21494@2 | `occt-2613378e60ff` | `2613378e60ff5e517b2bf73699184d0c6f636bb8` | `5ead8e62e4d72f801f43d8bd81dda610925dd2b9704ff51aaebe755def165104` | Clang 10, `-O0`, j1 |

## 校验与导入

从框架仓库根目录运行；使用独立且可写的数据库、cache、work 路径。路径按部署配置提供，使用已配置且包含所需依赖的 Conda 环境，不需要安装依赖。

```bash
: "${BENCH_CONDA_ENV:?set this to a configured Conda environment name}"
FRAMEWORK_ROOT="/absolute/path/to/agent_bench_web"
BUNDLE_ROOT="/absolute/path/to/occt-five-groups"
export PYTHONPATH="$FRAMEWORK_ROOT"
export BENCHMARK_ROOT="$BUNDLE_ROOT"
export BENCH_DATA_DIR="/absolute/path/to/isolated-bench-data"
export BENCH_CACHE_DIR="/absolute/path/to/isolated-source-cache"
export BENCH_WORK_DIR="/absolute/path/to/isolated-work"

conda run -n "$BENCH_CONDA_ENV" python -m backend.catalog --root "$BUNDLE_ROOT" --json
conda run -n "$BENCH_CONDA_ENV" python -m backend.import_proto
```

Suite/helper 路由按 suite `id@version` 白名单选择；DRAW runner 再按冻结 case-root 下的精确 checkpoint 相对路径白名单选择原 runner。未知 suite、未知 checkpoint、冲突映射及锁定 hash 不匹配都会失败关闭。路由与 helper hash 锁在 `evaluation/cases/evaluator_assets/five_group_execution/dispatch_lock.json`。G3 在 agent 模式保留真实几何 oracle，默认 `run_draw_case.py` 会传入 `--role agent`，不按二进制 hash 推断 B/F 身份。

## 源码缓存前置条件

题库不自带五个完整源码树。实际冻结任务前，框架必须在 `BENCH_CACHE_DIR/sources/<source_id>/` 下准备每个所选 source；`source.json` 中的 commit、tree SHA-256 和 `verified_git` 状态必须通过框架校验。当前本机缓存、逐组 freeze 和 `_prepare_control` 结果见 [迁移验收记录](../../integration-validation.json)；该记录不代表 fresh build 或几何重放。

框架不自动联网获取源码。先由操作者提供含对应固定 commit 的本地 OCCT Git checkout，再从框架仓库根目录逐个导入所需 source ID。`backend.source_cache` 会从本地 Git 对象执行 pinned commit 的 archive，重算 `materialized_tree_sha256`，只在哈希一致时写入只读 cache；不带 Git 元数据的 export 只能进入未验证状态，不能满足本组 freeze 的 `verified_git` 门槛。

```bash
SOURCE_ID="occt-2613378e60ff"  # 替换为上表中本次所选 group 的 source ID
LOCAL_GIT_CHECKOUT="/absolute/path/to/local-OCCT-checkout"
conda run -n "$BENCH_CONDA_ENV" env \
  PYTHONPATH="$FRAMEWORK_ROOT" \
  BENCHMARK_ROOT="$BUNDLE_ROOT" \
  BENCH_CACHE_DIR="/absolute/path/to/isolated-source-cache" \
  python -m backend.source_cache "$SOURCE_ID" --from-dir "$LOCAL_GIT_CHECKOUT"
```

对每个待运行的 source identity 分别执行一次，并确保本地 Git checkout 含表中完整 commit。历史 source bundle 已移到外部归档，不能替代已验证的 source cache；Part2 源树也不随本题库复制。

## 冻结快照 runner 命令

framework 在隔离 sandbox 内实际调用如下 runner 命令；`/evaluation` 与 `/workspace` 是 framework 挂载点，不是宿主机上的路径。应通过 framework evaluator/suite driver 启动，不要从宿主机直接运行这条容器内命令。

```bash
python /evaluation/suite_driver.py \
  --suite /evaluation/suite.json \
  --case-root /evaluation/cases/bundle \
  --patch /workspace/submission/patch.diff \
  --report /workspace/submission/report.md
```

`suite_driver.py` 从冻结快照读取所选 suite、case、helper 与 DRAW adapter；框架将验证过的 source cache 单独挂载到 `/evaluation/private/common_base_source`。运行仍按每个 group 自己锁定的 toolchain 和 evaluator 执行，不会因为统一 catalog 而合并任务。

## 交付范围

`MERGE_PROVENANCE.json` 记录输入 bundle 的 catalog/source-lock 摘要、来源映射及 dispatcher lock hash。两个大型 Git source bundle 和历史 BF 原始运行记录已移到 `$CADAI_ARCHIVE_ROOT` 指向的外部归档，保留 SHA256 与 Git refs；项目内题库可从已准备的 source cache 冻结，无需这些原始包。当前逐组 freeze、49 个 checkpoint 路由、helper/control 路径、工具链 preflight 和测试边界见 [迁移验收记录](../../integration-validation.json) 与 [外部归档清单](../../external-evidence-archive.json)。
