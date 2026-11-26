# 布尔截交的面域分类保留了多余的一段边

本题采用修复 #24286 同一提交明确修订的历史布尔截交原例 [boolean/bsection/L8](https://github.com/Open-Cascade-SAS/OCCT/blob/78c66ef1c92515f5d43d299f763348e6fe8d7a85/tests/boolean/bsection/L8)。它只计一道，不另外计入该提交新增的 General Fuse 脚本。[父版 B](https://github.com/Open-Cascade-SAS/OCCT/commit/a6eb515f9d6430bce09c4dcc0f088bcfea6bb6c6) 是[修复 F](https://github.com/Open-Cascade-SAS/OCCT/commit/78c66ef1c92515f5d43d299f763348e6fe8d7a85) 的直接父提交。固定[输入模型](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/GEN747_nofog.rle) 的 SHA-256 为 `0c1cf0dcc254e89da13f738fb36fc9f66e87f952f56137cad659abcb887a3687`。

`IntTools_FClass2d::Perform` 需要在面参数域里判断交点是否属于裁剪面。父版将面上的空间长度容差原值直接交给二维分类器；修复版用曲面的 U/V 分辨率换算成参数容差，并根据 UV 点落入的区间选择分量。自然父版误保留约 7.46331 mm 的截线。它仍是一个有效形体，因此单看 IsValid 不能判定正确。

| 输入 | 父版：边 / 点 / 总长 mm | 修复：边 / 点 / 总长 mm |
| --- | --- | --- |
| 原例 | 3 / 4 / 79.885527802753 | 2 / 3 / 72.422217828633 |
| 同移 (3, −2, 1) mm，改变坐标原点 | 3 / 4 / 79.885527802745 | 2 / 3 / 72.422217828673 |
| 交换子形，改变面上参数曲线的两侧角色 | 3 / 4 / 79.885527802747 | 2 / 3 / 72.422217828620 |
| 正交的两个有限平面 | 1 / 2 / 6 | 1 / 2 / 6 |

三例均检查有效性、2 边、3 点、长度 72.4222 ± 0.01 mm。对照要求有效、1 边、2 点和长度 6 ± 0.000001 mm。同一提交还改了 PaveFiller 的顶点映射。双向隔离采用同一探针和同一组输入：B 仅换 F 的二维分类器即三例全部恢复，F 仅换回 B 的分类器则三例全部复发。独立参考补丁因此只改一个源文件。

去重核对题库 main `6f44a316`、25 个全状态 PR head 与本地历史题单。模型名和 Git blob 仅在上游的数据集全量索引出现；没有已收录的题面使用此模型或此修复。#30354 的既有补丁也改动 IntTools_FClass2d，但针对分类器的多边形构造与 CSLib 二维分类，不是本题在 Perform 内将长度容差换成 U/V 参数容差的改动。
