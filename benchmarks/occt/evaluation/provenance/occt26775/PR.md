# 连续半空间差集中的步进交线越界

采用修复 [F d33a8cde](https://github.com/Open-Cascade-SAS/OCCT/commit/d33a8cde9649617a2fc433a58b98238136cc11a3) 实际修订面积期望的[上游 DRAW 原例 buc60532_2](https://github.com/Open-Cascade-SAS/OCCT/blob/d33a8cde9649617a2fc433a58b98238136cc11a3/tests/bugs/modalg_1/buc60532_2)。[自然父版 B](https://github.com/Open-Cascade-SAS/OCCT/commit/bf02aa7d7dcbdc460bef975913388ffc25d3d1a7)。两个半空间均由各自面形及指定点构造，按原序做两次 Cut。原例 B 和 F 都得到一个有效面，只有检查边界及面积才能揭示错误。

| 输入 | B 顶点/边/面/面积 | F 顶点/边/面/面积 |
| --- | --- | --- |
| 原例 | 8 / 8 / 1 / 81.6712 | 5 / 5 / 1 / 78.7016 |
| 全体平移 (1, −2, 3) | 8 / 8 / 1 / 81.6712 | 5 / 5 / 1 / 78.7016 |
| 绕 Z 轴旋转 25° | 8 / 8 / 1 / 81.7085 | 5 / 5 / 1 / 78.7390 |
| 两次轴对齐盒体差集 | 8 / 12 / 6 / 164 | 8 / 12 / 6 / 164 |

面积用平方模型单位，三例相同判据 78.7016 ± 0.1，并要求有效且 5 顶点、5 边、1 面。旋转后历史默认面积积分略有变化，不以最后一位浮点数判成败。正常例为 4 × 3 × 10 的长方体，面积 164 ± 0.00001。

**求交步骤。** F 在 `ComputePurgedWLine` 中、管状误差判据前，剔除不在两曲面参数域内的步进线采样点。只在 F 的单个编译单元中旁路 `DeleteOuterPoints` 的返回值，其他逻辑（包括后面的逼近）不动，就准确重现三组 B 面积；恢复该返回值则取得上表 F 几何。[保留清理](purge-intact.txt) / [旁路清理](purge-bypassed.txt)。原例能观测到 1002 个样点裁为 34、25 或 105 个，正常盒体结果不受此步影响。这与 #26841 已有种子时跳过面域交线构造器的缺陷不同。

该脚本和已收录的 #27780 共用前两个模型，但 #27780 检查曲面支持上参数曲线的端点方向；本题多一个边界面、两次半空间差集，并定位到不同直接父子提交的样点剔除。固定镜像逐文件：

- [buc60532a.brep](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/buc60532a.brep)，`c3cadb25981eb959c1cedca211ad3acd57f042e93592af36a992d159906249bb`。
- [buc60532b.brep](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/buc60532b.brep)，`112a74bf40af8540a084f29a3f628fdf0d62ff9ebeaa010f8ea04ff8a0f834dc`。
- [buc60532c.brep](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/buc60532c.brep)，`5458a0f6c8e3a58b2082308d5706fec0534fd94a3d067a2a93baad2fdf43511e`。
