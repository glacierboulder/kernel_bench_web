# 增加 OCCT #32701 退化边附近的截线回归基准

从第一个附件恢复支撑面，从第二个附件取第三张面，运行 `bsection`。在退化边附近，截边长度及拓扑均可正确，但三维曲线与支撑面参数曲线的对应精度会明显下降。判据要求有效形体、两个端点、单边长度 113.155 ± 0.01，并检查最大形体容差低于 3e−5。对每条边取 25 个含端点的等参数位置，分别在两个支撑面上计算曲线偏差，采样最大值应不超过 1e−6。[上游测试](https://github.com/Open-Cascade-SAS/OCCT/blob/9eee5ab7e413dccc6db1124327e8841e85854381/tests/lowalgos/intss/bug32701)

自然父提交为 `5614b1369a232f43e59cb9be4f5f8efd2075608d`，修复提交为 `9eee5ab7e413dccc6db1124327e8841e85854381`。变更在 `IntTools_FaceFace` 根据曲面估计 UV 步长，在 `ApproxInt` 根据曲率选择参数化方式，同时调整了 `BOPAlgo_PaveFiller` 在求交前对输入的位置处理。这组结果按整个上游补丁测量。[上游修复](https://github.com/Open-Cascade-SAS/OCCT/commit/9eee5ab7e413dccc6db1124327e8841e85854381)

| 工况 | 父提交最大形体容差 / 采样偏差 | 修复后最大形体容差 / 采样偏差 |
| --- | --- | --- |
| 公开原例 | 4.71423e−2 / 6.33117e−6 | 2.38296e−5 / 2.30823e−7 |
| 两面平移 (1, −2, 3) | 4.71427e−2 / 6.33117e−6 | 2.39251e−5 / 2.39909e−7 |
| 两面绕 Z 轴旋转 15° | 1.36052e−2 / 6.33118e−6 | 2.38384e−5 / 2.30039e−7 |
| 平面截边长 10 的立方体 | 四边均长 10，通过 | 四边均长 10，通过 |

修订题面的正式快照、参考补丁哈希及几何检查明细见[复评记录](round-offline.json)和[公开脚本运行记录](frozen-public-F.json)。

在题目目录运行 `DRAWEXE -b -f public/reproduce.tcl` 可复现公开原例。两个 BREP 附件均来自镜像版本 `d78a7a9e6de57699261fa03641ec1b5bafac39a1`。镜像说明列出了模型来源，未声明数据集统一许可。附件各自的许可未明确。[镜像说明](https://github.com/a-betenev/opencascade-dataset/tree/d78a7a9e6de57699261fa03641ec1b5bafac39a1)

- `brep/bug32701s.brep` 的 Git blob 为 `e5a9d78c4dd364e2c5d21e189f9eb9ebca9f8536`。[原文件](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/bug32701s.brep)
- `brep/bug32701t.brep` 的 Git blob 为 `a5ff117b2df4fb656ca804806c70d99d97a52b73`。[原文件](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/bug32701t.brep)

正式离线复评通过原例 1/1、邻域 2/2 和回归 1/1。[复评记录](round-offline.json)
