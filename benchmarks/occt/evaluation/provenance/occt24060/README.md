# OCCT 24060 · 方形面角点的重复布尔顶点

上游 [修复 c1746a0ac](https://github.com/Open-Cascade-SAS/OCCT/commit/c1746a0ac95425d8fd40dba08ab532adf74ae119) 的父版是 `9733d9b31b3f77a68443654541ddea5030b3d1f7`。[DRAW 原例](https://github.com/Open-Cascade-SAS/OCCT/blob/c1746a0ac95425d8fd40dba08ab532adf74ae119/tests/bugs/modalg_5/bug24060) 直接建立平面四边形和独立顶点。题包内的 C++ 复现程序通过 `BOPAlgo_Builder` 执行相同的 General Fuse。

| 检查点 | 自然父版 | 自然修复版 |
|---|---|---|
| 公开原例 | 5 顶点，角点有 2 个重合顶点 | 4 顶点，角点只有 1 个 |
| 交换输入顺序 | 5 顶点，角点有 2 个 | 4 顶点，角点只有 1 个 |
| 沿 X 平移 3.5 | 5 顶点，角点有 2 个 | 4 顶点，角点只有 1 个 |
| 顶点离开面至 Y=2 | 5 顶点，独立顶点保留 | 5 顶点，独立顶点保留 |

所有结果均有效，包含 4 条边、1 个面，面积为 1。修复在 `BOPAlgo_PaveFiller` 的顶点–边和顶点–面干涉阶段初始化相应边段与面信息，并登记落在面内的顶点。参考补丁保留上游两处生产文件修改。题面只公开原例，另三例分别编译、独立评分。

冻结公开命令、双版本几何实测及断网正式评分结果见本题 `evidence/`；题库补丁中的 `evaluation/provenance/occt24060/` 保留对应记录。
