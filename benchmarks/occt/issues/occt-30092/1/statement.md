# 布尔截线在同域顶点附近失效并产生错误长度

用一条容差为 0.04 的短线段切分输入的第二个曲面，再计算该曲面与第一个曲面及短线段的截线。预期得到有效截线，包含 5 个顶点、4 条边，总长约 1250.44。

在题目目录运行 `DRAWEXE -b -f public/reproduce.tcl` 可查看截线拓扑和长度。随附模型为 OCCT 7.5.0 官方测试数据发行批次中的 `bug26795_c.brep`。[模型来源](https://github.com/a-betenev/opencascade-dataset/blob/12ec0ea9af6db153903fe0cf57ff5c4f30f66830/brep/bug26795_c.brep)

冻结任务：进入与本题面同目录的公开输入目录（即题面所在目录），运行 `DRAWEXE -b -f reproduce.tcl`。在题库源码的题目目录下则运行 `DRAWEXE -b -f public/reproduce.tcl`。
