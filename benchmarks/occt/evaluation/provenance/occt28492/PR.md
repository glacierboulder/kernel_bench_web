# 增加 OCCT #28492 短步长截线回归基准

公开脚本对上游第三组实体附件 `a350`、`b350` 求 Boolean Section。分别从两个模型得到 7 张和 6 张支撑面。自然父提交为 `176a7959209e938a9b57a6eb900f4a5488829e43`，修复提交为 `3b6ffeaca7c1dad2213395301f59da18d1960b82`。生产代码只修改 `IntWalk_PWalking::Perform`，允许步进交线在局部采用小于传入三维容差的步长，步长下限为 `Precision::Confusion()`。[上游修复及测试](https://github.com/Open-Cascade-SAS/OCCT/commit/3b6ffeaca7c1dad2213395301f59da18d1960b82)

| 工况 | 父提交 | 修复后 |
| --- | --- | --- |
| 公开原例 | 24 条边、30 个顶点，有 8 条长度 0.02516 至 0.06057 的短边 | 18 条边、16 个顶点，两条相关截边长 0.666548、0.666549 |
| 两模型平移 (1, −2, 3) | 24 条边、30 个顶点 | 18 条边、16 个顶点，两条相关截边长 0.666548、0.666549 |
| 两模型绕 Z 轴旋转 15° | 24 条边、30 个顶点 | 18 条边、16 个顶点，两条相关截边长 0.666519、0.666543 |
| 平面截边长 10 的立方体 | 4 边、4 顶点，边长均为 10 | 4 边、4 顶点，边长均为 10 |

四个工况中两版形体均有效。验收检查截线顶点数、边数和排序后的整组边长，逐边允许误差 0.001。公开复现命令为 `DRAWEXE -b -f public/reproduce.tcl`。

修订题面的正式快照、参考补丁哈希及几何检查明细见[复评记录](round-offline.json)和[公开脚本运行记录](frozen-public-F.json)。

镜像提交 `d78a7a9e6de57699261fa03641ec1b5bafac39a1` 保存了两个模型的原始 BREP 字节。题包添加 `.brep` 扩展名。镜像说明列出了模型来源，未声明统一的数据集许可，两个附件的独立许可未明确。[镜像说明](https://github.com/a-betenev/opencascade-dataset/tree/d78a7a9e6de57699261fa03641ec1b5bafac39a1)

- `brep/a350` 的 Git blob 为 `0ecf64de04c31073c05a9fcae2c16bd712960d4b`。[原文件](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/a350)
- `brep/b350` 的 Git blob 为 `7baaa946fa01aeee9637d6ecab32c9b6053e2297`。[原文件](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/b350)

正式离线复评通过原例 1/1、邻域 2/2 和回归 1/1。[复评记录](round-offline.json)
