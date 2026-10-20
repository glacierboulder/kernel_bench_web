# 手工维护题库

题库由版本化文件维护，网页目前没有题目编辑器。可复制 [完整小题库示例](benchmark-example/)，它包含两个 issue、一个单题组、一个组合题组、两套检查点清单、源码锁、工具链和来源记录。所有清单都在项目代码外，接入新题目不需要修改后端。

## 在临时目录校验和导入

在仓库根目录、已安装框架依赖的 Conda 环境中运行。先设置该环境名；下面的临时目录和 SQLite 数据库只用于本次验证：

```bash
: "${BENCH_CONDA_ENV:?set this to a configured Conda environment name}"
BENCH_AUTHORING_TMP="$(mktemp -d)"
cp -a docs/benchmark-example "$BENCH_AUTHORING_TMP/benchmark"
export BENCHMARK_ROOT="$BENCH_AUTHORING_TMP/benchmark"
export BENCH_DATA_DIR="$BENCH_AUTHORING_TMP/data"
unset BENCH_PROTO_ROOT
conda run -n "$BENCH_CONDA_ENV" python -m backend.catalog --json
conda run -n "$BENCH_CONDA_ENV" python -m backend.import_proto
```

导入后，题目选择列表会有 `manual-box-a-single` 和 `manual-box-pair` 两个 ID。若只想验证清单而不写数据库，可只运行 `backend.catalog`。显式设置 `BENCHMARK_ROOT` 时不会从仓库旁边的旧 `OCCT_bench_proto` 目录兼容导入题目。

实际部署时，将复制后的题库目录配置为 `BENCHMARK_ROOT`，并把 `BENCH_DATA_DIR` 指到该部署专用的数据目录。题目导入只写这个数据库；它不准备源码缓存，也不会启动 worker 或模型任务。真实执行还要求锁定基线已经通过源码缓存校验。

## 文件和标识怎么更新

| 修改内容 | 更新文件和标识 |
| --- | --- |
| 新增 issue | 新建 `issues/<issue-id>/<version>/issue.json`、题面和公开输入；将该 ID/version/path 加入 `catalog.json` 的 `issues`。 |
| 修改题面、公开输入或 issue 基线 | 原 issue 目录保持不变；新建该 issue 的新版本目录并更新 `catalog.json` 引用。基线变化还要新增 `sources.lock.json` 条目以及对应工具链/来源记录。新建组来引用新 issue 版本。 |
| 新增题组或改变成员、预算、执行模式、产物要求 | 新建 `groups/<new-group-id>/<version>.json`，并在 `catalog.json` 添加新 ID。当前禁止同一组 ID 出现两个版本；不要用原 ID 的版本号覆盖更新。 |
| 只增加、删除或调整检查点 | 复制 suite 清单到新的 suite 版本路径，改 suite 的 `version` 和 `catalog.json` 引用。不要改 issue 或其输入。旧补丁可以显式选择这个新 suite 复评。 |
| 让新 suite 成为后续任务的默认检查 | suite 新版本之外，再新建一个题组 ID，让该组引用新 suite；旧题组和 suite 保留给历史记录。 |

Suite 的 `case` 是检查文件唯一来源。DRAW 检查直接把这个文件名传给 `--script`；不要在 `runner_options` 中再写 `script`。每次改完都在临时副本上执行上面的校验和导入命令。校验器会检查版本引用、源码基线、suite 兼容关系、runner 类型和所有 case 文件是否存在。

## 目录结构

```text
my-benchmark/
  catalog.json
  sources.lock.json
  toolchains/<toolchain-id>.json
  evaluation/provenance/<source-provenance>.json
  evaluation/suites/<suite-id>/<version>.json
  issues/<issue-id>/<version>/{issue.json,statement.md,public/*}
  groups/<new-group-id>/<version>.json
```

`docs/benchmark-example/` 可以直接复制后改名和内容。示例的源码锁引用本项目已经验证过的 OCCT 基线；它验证题库接入格式，不会复制 OCCT 源码缓存，也不会运行示例检查。
