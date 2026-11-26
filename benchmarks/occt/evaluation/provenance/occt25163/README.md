# OCCT 25163 · 圆柱面的公共区域丢失

上游 [修复 fc88faf18](https://github.com/Open-Cascade-SAS/OCCT/commit/fc88faf18a2d3e55c036322e1bb966ec218278c5) 的自然父版为 `1d33d22bd73928f0c38a3b9f681f7b0ca598af7b`。[DRAW 原例](https://github.com/Open-Cascade-SAS/OCCT/blob/fc88faf18a2d3e55c036322e1bb966ec218278c5/tests/bugs/modalg_5/bug25163) 从公开模型抽取两个面执行 Common。题包附原始模型和可编译的回放程序。

| 检查点 | 自然父版 | 自然修复版 |
|---|---|---|
| 公开原例 | 0 面，面积 0 | 1 面，面积 3417.7118648226 |
| 平移两面 | 0 面，面积 0 | 1 面，面积 3417.7118648226 |
| 交换两面 | 0 面，面积 0 | 1 面，面积 3417.7120016055 |
| 共面矩形重叠 | 1 面，面积 8 | 1 面，面积 8 |

修复版的三个触发例各有 4 个顶点、4 条边、1 个壳，形体有效。上游同时修改了参数曲线的周期调整与组线时的二维角度细化。将修复版 `BOPTools_AlgoTools2D` 单独链接进父版即恢复公共面，单独替换 `WireSplitter` 仍为空。故参考补丁只采用已隔离的参数曲线修改，用圆柱半径与边容差确定角容差，将偏出范围的参数曲线移回合适的周期。

[公共模型](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/bug25163_qf_25_39.brep)。完整命令、评分及双版本回放记录随题附于 `evidence/`。
