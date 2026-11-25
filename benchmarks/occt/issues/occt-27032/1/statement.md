# 边界边与截线重合时，Section 漏掉一段交边

对附带复合体中的两个形状求 Section，完整截线应含 4 条边和 4 个顶点，总长约 3606.37。其中有两条长约 1480.5 的交边。按公开顺序计算布尔差时，结果面积约为 1809490。用 `DRAWEXE -b -f public/reproduce.tcl` 复现。

冻结任务：进入与本题面同目录的公开输入目录（即题面所在目录），运行 `DRAWEXE -b -f reproduce.tcl`。在题库源码的题目目录下则运行 `DRAWEXE -b -f public/reproduce.tcl`。
