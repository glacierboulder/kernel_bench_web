# OCCT 共用运行基础设施

## 统一范围

当前默认题库 `benchmarks/occt` 已包含旧五个问题组及 v4 十个单题。这十五个任务共有 113 个检查点，使用框架维护的同一个监督端适配器 `backend/runtime/occt_adapter.py`。

共用的部分包括：冻结与材料校验、测试副本定位、检查点路由、超时/CPU/内存限制、补丁与构建调用入口、结果封装，以及模型可用的公开构建和 DRAW 自测入口。公开工具不依赖隐藏用例或私有检查点锁。

历史五组的几何解析器和不同 OCCT 版本所需的构建兼容实现仍作为哈希固定的依赖调用。它们保留原来的数值阈值及判定语义；这些历史实现不作为后续新题的适配器模板。编译器、优化级别和版本兼容条件属于源码/工具链配置，不能为了让代码相同而抹平。

旧快照保留原始运行代码。统一基础设施只影响之后创建的快照和显式复评，不回写历史运行。

## 后续新题：只增加题目数据和依赖

使用既有源码和工具链时，新增题目只需增加：

1. `issue.json`、题面、公开输入与必要的复现材料。
2. group 和 suite 清单。
3. 原始、邻域、健康回归脚本，以及 `support_files` 中显式列出的依赖。
4. 每个 DRAW 检查点的断言 ID 清单。

不新增 `run_draw_case.py`、`run_eval.py`，也不复制另一套路径检查或日志解析器。需要新的 OCCT 源码时，另外扩展 `sources.lock.json` 和可复用的工具链配置；不按题目创建工具链代码。

标准检查点示例：

```json
{
  "id": "original-volume",
  "issue_id": "mantis-example",
  "category": "original",
  "visibility": "hidden",
  "runner": "draw_case_v1",
  "case": "issues/mantis-example/1/original.tcl",
  "oracle": "draw_test_done_v1",
  "timeout_seconds": 180,
  "required": true,
  "runner_options": {
    "expected_assertion_ids": ["shape_valid", "volume"]
  }
}
```

`expected_assertion_ids` 是结果中必须恰好出现一次的断言名称。脚本输出格式为：

```text
BENCH_ASSERT_PASS shape_valid ... kind=expression
BENCH_ASSERT_PASS volume ... kind=numeric
__BENCH_ORACLE_COMPLETE__
BENCH_ORACLE_OK assertions=2 numeric_assertions=1
TEST_DONE assertions=2 numeric_assertions=1
```

失败断言使用 `BENCH_ASSERT_FAIL`。脚本必须先执行真实几何判断，再输出对应结果。完成标记本身不能证明几何正确。必要时用 `expected_failure_lines` 声明官方几何检查的已知错误文本；不能把启动失败、缺文件或 Tcl 语法错误列为预期几何失败。

冻结时，框架自动生成私有运行契约、计算脚本哈希并带入共用适配器。新标准题不需要手工登记 `evaluation/runtime.json`；该文件用于迁移已有十五个任务的历史接口。

## 路径约定

冻结材料只读保存。正式执行前，套件执行器创建自己的可写副本，供 DRAW 写日志和测量文件，并通过 `BENCH_FROZEN_CASE_ROOT` 告知适配器副本根目录。

适配器按该根目录定位检查点，同时检查路径包含关系、登记的相对路径及脚本哈希。不得写死 `/evaluation/cases/bundle`，不得依据宿主绝对路径决定几何结果。

动态库目录、DRAW 启动文件和资源路径由共用适配器根据本次选择的 build/resource 目录设置，避免继承其他任务的旧环境变量。

## 结果状态

共用结果包含 `status`、`oracle_ran`、`passed`，并保留 `raw_result`：

| 状态 | 含义 | 套件归类 |
|---|---|---|
| `geometry_pass` | 几何判据实际运行并通过 | passed |
| `geometry_fail` | 几何判据实际运行并拒绝结果 | failed |
| `timeout` | 资源限制内没有完成判定 | timeout |
| `runner_error` / `oracle_incomplete` | 执行入口、依赖或判据输出不完整 | error |
| `not_run` | 判据未运行 | not_run |

不能将进程返回 0 当成几何通过，也不能将缺文件、路径错误或缺动态库记成几何失败。

## 严格校验与效率

严格校验是同一次执行中的本地操作：检查点路由查询、材料哈希及输出断言核对。不增加模型请求，不启动第二次构建，也不为了验证输出再次执行几何用例。

参考重放可以复用已验证的参考构建；补丁正式评测仍应用补丁并构建一次。未来优化缓存必须按源码、补丁、工具链和依赖哈希匹配，不能复用来源不明的二进制。

## 接入验证

在 conda 环境中运行：

```bash
python -m unittest tests.test_occt_runtime tests.test_suite_driver
python scripts/experiments/validate_occt_bundle_routes.py
```

第二个命令检查新的冻结、监督端控制目录、公开工具及全部路由，不运行几何。正式接入还需可信参考的实际几何重放，并用失败/缺断言/篡改材料等负对照确认错误能被拒绝。不要以导入成功代替完整评测链路验证。
