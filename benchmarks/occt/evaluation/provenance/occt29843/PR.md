# OCCT #29843 远离原点的实体布尔求交丢失截线边

本题取自上游 `tests/bugs/modalg_7/bug29843_2`。两个实体的坐标量级约为 10⁸；上游修复在计算远离原点的对象之间的交点时将几何体移近原点，以提高精度。B 为 `d7992a77f6fdf558ed7bcfcbd1117ce2d715c9db`，F 为 `c08fd127066e78d3427955b8d3a11dd880fe3244`。[上游修复](https://github.com/Open-Cascade-SAS/OCCT/commit/c08fd127066e78d3427955b8d3a11dd880fe3244) · [上游回归用例](https://github.com/Open-Cascade-SAS/OCCT/blob/c08fd127066e78d3427955b8d3a11dd880fe3244/tests/bugs/modalg_7/bug29843_2)

`bfillds` 建立干涉数据后，`bbop section 4` 提取截线，`bbop result 0` 计算公共实体。原例及两个邻域应返回 6 个截线顶点、7 条边，总长约 952.189；公共部分应为包含 5 个面的单个有效实体，通过 `bopcheck`，体积约为 1,176,100。两个邻域分别整体平移 (1, 3, −2) 和互换两个操作数。健康对照用部分重叠的长方体构造，预期截线有 6 个顶点和 6 条边，总长 20，公共体积为 36。

`bug29843_loc.brep` 来自 OCCT 7.5.0 测试数据集，镜像导入提交为 `12ec0ea9af6db153903fe0cf57ff5c4f30f66830`，文件 Git blob 为 `49ebb659d10569773fd8496ba7022dc806ca4b0b`，SHA-256 为 `637ab1d2e5dd7324255b564051fb2125f20793dc1586703a8ede88c571835e69`。镜像说明列明来源，未列出单独的模型许可条款。[官方公告](https://occt3d.com/dev/content/open-cascade-technology-testing-dataset-published/) · [镜像文件](https://github.com/a-betenev/opencascade-dataset/blob/12ec0ea9af6db153903fe0cf57ff5c4f30f66830/brep/bug29843_loc.brep)

| 工况 | B 截线（顶点、边、长度） | B 公共实体数、体积 | F 截线（顶点、边、长度） | F 公共实体数、体积 |
| --- | --- | --- | --- | --- |
| 原例 | 4，4，785.231 | 0，0 | 6，7，952.189 | 1，1,176,100 |
| 整体平移 | 4，4，785.231 | 0，0 | 6，7，952.189 | 1，1,176,100 |
| 互换操作数 | 4，4，785.231 | 0，0 | 6，7，952.189 | 1，1,176,100 |
| 长方体对照 | 6，6，20 | 1，36 | 6，6，20 | 1，36 |

两个版本的 `checkshape` 和 `bopcheck` 对公共结果均报通过。B 在三个缺陷输入上实际返回空结果，实体计数和体积检查可检出这一差异。

最终题面的冻结离线复评通过原例 1/1、邻域 2/2、对照 1/1，快照 SHA-256 为 `b12a7b67c1048157dc46e61528620d779cefcf8b59c3b7ac5c3c2ad5bbe54302`。同一快照的公开脚本在自然 F 上得到长度 952.189 的 7 边截线，公共实体体积为 1,176,100。[离线复评](round-offline.json) · [公开脚本运行记录](frozen-public-F.json)

正式离线复评通过原例 1/1、邻域 2/2 和回归 1/1。[复评记录](round-offline.json)
