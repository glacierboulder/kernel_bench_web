# OCCT 23998：第二轮单题核查

当前状态：**候选，未注册，不能授予正式通过**。

[模型所见题目描述](../../../../benchmarks/occt/issues/occt-23998/1/statement.md)

本轮修正：新增逐边 21 点到两个有界输入面的距离；整体平移错误截线会被拒绝。正常回归改为实际执行 bop/bopsection，旧的直接构造圆检查不能证明算法正常。

本机 B 原例：`geometry_fail`。F 的原例、两个邻域、正常回归共 4 项均通过当前本地必要检查；B 正常回归也通过。该结论不等于独立完整几何证明或正式评测通过。

构建审计：当前构建器拒绝 6.6。真实 Linux 构建、源码缓存导入、冻结沙箱 B/F 重放均未完成。Windows 上采用相同的浮点异常屏蔽兼容加载器，不是 Linux 原生运行证据。

| 角色 | 检查 | 本地结果 | 秒数 | 原始日志 |
|---|---|---|---:|---|
| B | neighbor_rotate | geometry_fail | 0.482 | [日志](logs/B-neighbor_rotate.txt) |
| B | neighbor_translate | geometry_fail | 0.461 | [日志](logs/B-neighbor_translate.txt) |
| B | original | geometry_fail | 0.455 | [日志](logs/B-original.txt) |
| B | regression | geometry_pass | 0.234 | [日志](logs/B-regression.txt) |
| F | neighbor_rotate | geometry_pass | 0.461 | [日志](logs/F-neighbor_rotate.txt) |
| F | neighbor_translate | geometry_pass | 0.46 | [日志](logs/F-neighbor_translate.txt) |
| F | original | geometry_pass | 0.465 | [日志](logs/F-original.txt) |
| F | regression | geometry_pass | 0.236 | [日志](logs/F-regression.txt) |
| negative | original | geometry_fail | 0.465 | [日志](logs/negative-original.txt) |
| translated_result | original | geometry_fail | 0.452 | [日志](logs/translated_result-original.txt) |

错误结果负对照使用作者私有 Tcl 副本，检查判分器会不会放过明显错误；不是重新编译 C++ 负补丁。所有原始日志均有 SHA-256，详见上级 native-replay.json。

[历史截图与原始报告（已标记取代）](../../occt-23998/report.html)。截图来自先前本机运行，不能代替本轮已更新断言的原始日志。
