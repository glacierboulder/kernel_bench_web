# #25450：边面干涉后差集边界缺面

**范围。** [修复 ceb31c61](https://github.com/Open-Cascade-SAS/OCCT/commit/ceb31c6156839c4a96563cbe288fdc1e3bc3cc46) 同时把既有公开 [bug497_3](https://github.com/Open-Cascade-SAS/OCCT/blob/ceb31c6156839c4a96563cbe288fdc1e3bc3cc46/tests/bugs/modalg_2/bug497_3) 的面积参考由 1773.60 改为 2471.48。我们采用该测试的 CUT，而非宣称已取得工单原始 COMMON 附件 `bug25450_Shape.brep`。固定 [OCC497e.brep](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/OCC497e.brep) 与 [OCC497f.brep](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/OCC497f.brep)，按原 DRAW 命令先做 `PaveFiller` 后作布尔差。

**自然版差分。** B 是 F 的直接父版 `93442c6f24ea0e7afc058e81ef2eee2f1b085d3b`。两输入上的局部接触保持不变。新增盒置于 (1000,1000,1000)，尺寸 2×3×4，边界面积 52。

| 构型 | B：面积 / 面数 / 实体数 | F：面积 / 面数 / 实体数 |
|---|---:|---:|
| 公开切割原例 | 1773.596418 / 2 / 1 | 2471.482555 / 8 / 1 |
| 工具中增加不接触的盒，面积应不变 | 1773.596418 / 2 / 1 | 2471.482555 / 8 / 1 |
| 对象中增加独立盒，面积应加 52 | 1825.596418 / 8 / 2 | 2523.482555 / 14 / 2 |
| 保护：切掉边长 10 盒的一半 | 400 / 6 / 1 | 400 / 6 / 1 |

**首个观测分歧。** 两版都找出边 9、14 和面 30 的 EF 干涉。B 的待更新面集合不含面 30，F 包含面 30，随后可见 `UpdateFaceInfoIn(30)`。两版最终结果均通过拓扑检查，但 B 少 6 个面。这是 EF 后处理差异，不是布尔结果有效性检查本身的缺陷；正式套件不含插桩。

**限制。** 原例共同平移 (1,3,-2) 或绕 Z 轴旋转 0.13 rad 后，F 也错误返回面积 1773.596418。两项未计分且保留在 `initial-rigid-*.log`。本提交只验收表中两种明确可判定的几何扩展，不宣称 F 完整解决位姿敏感性。

**验收材料。** `result.json` 给出离线套件分类计数，`source-import.json` 锁定源码，`frozen.json` 和 `frozen-all-checkpoints.json` 绑定冻结公开输入和各端实测结果，`stage-B.log`、`stage-F.log` 保存中间证据。不修改后端，无远程发布操作。
