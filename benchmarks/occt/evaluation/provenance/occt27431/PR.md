# 增加 OCCT #27431 的圆柱与球面 Boolean Section 基准

从两个公开附件恢复半径均为 20 的圆柱面和球面。圆柱使用整个周向区间，轴向范围为 [−10, 10]。球心沿全局 Z 轴偏移 0.02 后，两张面相交形成靠近球极点的一条闭合截线。公开输入采用这组重新修剪并偏置的支撑面。原上游脚本对原修剪面调用 `bopcurves`。[上游测试](https://github.com/Open-Cascade-SAS/OCCT/blob/e2e0498b17acc86bdd64d3322ad2e9eb203e387f/tests/bugs/modalg_6/bug27431)

在局部圆柱坐标系中，用 t 表示周向参数、x 表示轴向位置、R 表示半径、d 表示球心偏置。代入球面方程得到 x² = 2Rd sin(t) − d²。分别在 x 的正负分支上积分，参考总长约为 125.8173。两版原例都在总长的 ±0.02 误差带内。判据同时要求有效形体、两条边、两个顶点、形体容差小于 0.005，并逐边在 25 个参数位置校验三维曲线与两张支撑面的对应参数曲线，最大偏差限值为 1e−5。

父提交为 `416022a12ff2315850442a0244f59d61888e17e0`，修复提交为 `e2e0498b17acc86bdd64d3322ad2e9eb203e387f`。上游在解析交线向步进交线转换时重写了极点等特殊位置的处理。实测数据来自完整上游变更。[修复提交](https://github.com/Open-Cascade-SAS/OCCT/commit/e2e0498b17acc86bdd64d3322ad2e9eb203e387f)

| 工况 | 父提交形体容差 / 最大采样偏差 | 修复后形体容差 / 最大采样偏差 |
| --- | --- | --- |
| 偏置球面与圆柱原例 | 0.103528 / 0.0662942 | 0.00141923 / 2.60734e−7 |
| 两面共同平移 (1, −2, 3) | 0.103528 / 0.0662942 | 0.00141923 / 2.60736e−7 |
| 两面绕 Z 轴旋转 15° | 0.103528 / 0.0662942 | 0.00141923 / 2.60735e−7 |
| 平面截边长 10 的立方体 | 四边均长 10，通过 | 四边均长 10，通过 |

原例父提交两条边长度分别为 32.2815 和 93.5359，修复后为 32.2813 和 93.5295。运行 `DRAWEXE -b -f public/reproduce.tcl` 可查看拓扑、线长和容差。

修订题面的正式快照、参考补丁哈希及几何检查明细见[复评记录](round-offline.json)和[公开脚本运行记录](frozen-public-F.json)。

附件来自公开数据集镜像的 `d78a7a9e6de57699261fa03641ec1b5bafac39a1` 版本，镜像中没有统一的数据集许可声明，附件的独立许可未明确。[镜像说明](https://github.com/a-betenev/opencascade-dataset/tree/d78a7a9e6de57699261fa03641ec1b5bafac39a1)

- `brep/OCC13116_sh1.brep` 的 Git blob 为 `84a4584583bf51246c2f4fef12da95a9f329043a`。[原文件](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/OCC13116_sh1.brep)
- `brep/OCC13116_sh2.brep` 的 Git blob 为 `7dd5713e18a5cbb992f9eaa56948872112e7064a`。[原文件](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/OCC13116_sh2.brep)

正式离线复评通过原例 1/1、邻域 2/2 和回归 1/1。[复评记录](round-offline.json)
