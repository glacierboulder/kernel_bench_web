# OCCT 30198：第二轮单题核查

当前状态：**候选，未注册，不能授予正式通过**。

[模型所见题目描述](../../../../benchmarks/occt/issues/occt-30198/1/statement.md)

本轮修正：保留内存限制复现和实体/面/体积约束，新增表面积一致性检查；正式资源阈值仍需 Linux 标定。

本机 B 原例：`memory_limit`。F 的原例、两个邻域、正常回归共 4 项均通过当前本地必要检查；B 正常回归也通过。该结论不等于独立完整几何证明或正式评测通过。

构建审计：仅版本分派识别，Linux 实建未跑。真实 Linux 构建、源码缓存导入、冻结沙箱 B/F 重放均未完成。Windows 上采用相同的浮点异常屏蔽兼容加载器，不是 Linux 原生运行证据。

| 角色 | 检查 | 本地结果 | 秒数 | 原始日志 |
|---|---|---|---:|---|
| B | original | memory_limit | 9.116 | [日志](logs/B-original.txt) |
| B | regression | geometry_pass | 0.231 | [日志](logs/B-regression.txt) |
| F | neighbor_reverse | geometry_pass | 27.521 | [日志](logs/F-neighbor_reverse.txt) |
| F | neighbor_shift | geometry_pass | 27.944 | [日志](logs/F-neighbor_shift.txt) |
| F | original | geometry_pass | 27.598 | [日志](logs/F-original.txt) |
| F | regression | geometry_pass | 0.238 | [日志](logs/F-regression.txt) |
| negative | original | geometry_fail | 21.498 | [日志](logs/negative-original.txt) |

错误结果负对照使用作者私有 Tcl 副本，检查判分器会不会放过明显错误；不是重新编译 C++ 负补丁。所有原始日志均有 SHA-256，详见上级 native-replay.json。

[历史截图与原始报告（已标记取代）](../../occt-30198/report.html)。截图来自先前本机运行，不能代替本轮已更新断言的原始日志。
