# 边界边与截线重合时，Section 漏掉一段交边

对附带复合体中的两个形状求 Section，完整截线应含 4 条边和 4 个顶点，总长约 3606.37。其中有两条长约 1480.5 的交边。按公开顺序计算布尔差时，结果面积约为 1809490。用 `DRAWEXE -b -f public/reproduce.tcl` 复现。[上游修复](https://github.com/Open-Cascade-SAS/OCCT/commit/05cf4d98b05f5e579e17ec2bf1bae1e8b6ce5698)

原例、共同平移以及交换 Section 两操作数分别检查截线。正常对照使用解析方盒。测量见 [B 日志](natural-B.txt) 和 [F 日志](natural-F.txt)。

自然父提交 `7d835040071b` 的三个缺陷输入都漏掉一条长约 1480.5 的边，截线由 3 条边构成，总长 2125.87。修复提交 `05cf4d98b05f` 恢复 4 条边，总长 3606.37。差集面积由约 1894430 变为 1809490。方盒对照在两版都得到 6 条截边，总长 30。

模型文件也包含在 OCCT 7.8.0 官方公开测试数据包内。镜像提交为 `d78a7a9e6de57699261fa03641ec1b5bafac39a1`。模型 SHA-256 为 `5c1e4e79b31b5db74371eccd35897a11acc8d70e8ffa49fd9fe8cfd56292a530`。数据包未列单个模型的独立许可。[官方测试数据](https://github.com/Open-Cascade-SAS/OCCT/releases/download/V7_8_0/opencascade-dataset-7.8.0.tar.xz) · [镜像来源说明](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/Readme.md)

正式离线复评通过原例 1/1、邻域 2/2 和回归 1/1。[复评记录](round-offline.json)
