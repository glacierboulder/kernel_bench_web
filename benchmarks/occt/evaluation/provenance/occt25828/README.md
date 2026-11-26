# #25828：截交曲线覆盖缺失

**范围。** 以修复 [c8187bb2](https://github.com/Open-Cascade-SAS/OCCT/commit/c8187bb218b658b71da96da46eb2105795c897cb) 同时更新的公开回归 [boolean/bsection/R9](https://github.com/Open-Cascade-SAS/OCCT/blob/c8187bb218b658b71da96da46eb2105795c897cb/tests/boolean/bsection/R9) 作为本题原例。这是已存在的 BUC60462 算例，不是工单最初报障的 `bug25828_intersectionproblem.brep`，也不声称复现该附件。公开输入 [buc60462a.brep](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/buc60462a.brep) 和 [buc60462b.brep](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/buc60462b.brep) 随题冻结；不是旧题引用的同前缀 c/d 文件。

**自然版差分。** B 是 F 的直接父版 `5bffb8828265a829f7f938639a92076294a62cff`。下表为 `BRepAlgoAPI_Section` 输出，均为有效拓扑。

| 构型 | B：总长 / 边数 | F：总长 / 边数 |
|---|---:|---:|
| R9 原例 | 261.261890 / 17 | 264.046080 / 18 |
| 两输入共移 (1,3,-2) | 261.261890 / 17 | 264.046080 / 18 |
| 两输入绕 Z 轴转 0.13 rad | 261.261776 / 17 | 264.045966 / 18 |
| 保护：两个不同位置的平面截段 | 20 / 2 | 20 / 2 |

**判据来源。** R9 的参考由 261.262 改为 264.314。[上游公共判据](https://github.com/Open-Cascade-SAS/OCCT/blob/c8187bb218b658b71da96da46eb2105795c897cb/tests/boolean/end) 是相对误差不超过 1%，非精确等于。初次自行采用绝对误差 0.02 时 F 也失败；保留 `initial-strict-*.log`，最终按原判据重测。保护例另断言两条独立截边及各自合计的解析长度。

**首个观测分歧。** 仅用于诊断的插桩记录到同一对 3 点步进候选：旧候选折线长 0.165120，新候选长 0.912832。B 保留旧候选，F 替换它。正式版没有插桩；整个生产差分限定在 `IntPatch_PrmPrmIntersection.cxx`。虽然最终拓扑有效，B 会少一个截段；仅检查是否成功或是否有效均检不出。

**验收材料。** 原例、两个邻域和保护例在同一离线套件独立裁决；`result.json` 给出分类计数，`source-import.json` 绑定自然父版，`frozen.json` 和 `frozen-all-checkpoints.json` 绑定冻结材料及两端回放，`stage-B.log`、`stage-F.log` 保存内部观测。工程范围限题库条目，不修改基准后端；提交物为单个本地 mbox。
