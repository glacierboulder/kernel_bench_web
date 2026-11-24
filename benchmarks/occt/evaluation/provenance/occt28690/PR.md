# 平面与面组的 Section 结果含无有效参数区间的微边

附带的面组经过平移后与 x=0 平面相交。结果应为三条可用截边和四个顶点，总长约 594.045。每条边都应有超出其端点公差区域的有效参数区间。用 `DRAWEXE -b -f public/reproduce.tcl` 检查截线拓扑、长度和逐边有效区间。[上游修复](https://github.com/Open-Cascade-SAS/OCCT/commit/8ae442a8cbcd50d4c59a7024b198646123387579)

原例、共同平移以及交换 Section 两操作数分别检查截线。正常对照使用解析方盒。测量见 [B 日志](natural-B.txt) 和 [F 日志](natural-F.txt)。

自然父提交 `f5b7241978a9` 的三个缺陷输入均含 3 边、3 点，其中一条边没有有效参数区间。修复提交 `8ae442a8cbcd` 的三个结果均含 3 边、4 点，每条边均有有效区间。总长均约为 594.045。方盒对照两版均保留 4 条有效截边，总长 40。

模型文件也包含在 OCCT 7.8.0 官方公开测试数据包内。镜像提交为 `d78a7a9e6de57699261fa03641ec1b5bafac39a1`。模型 SHA-256 为 `5c989240a9303b54a84dd0b9f3df5537e65209e7b72103eeed610f6dc67845ec`。数据包未列单个模型的独立许可。[官方测试数据](https://github.com/Open-Cascade-SAS/OCCT/releases/download/V7_8_0/opencascade-dataset-7.8.0.tar.xz) · [镜像来源说明](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/Readme.md)

正式离线复评通过原例 1/1、邻域 2/2 和回归 1/1。[复评记录](round-offline.json)
