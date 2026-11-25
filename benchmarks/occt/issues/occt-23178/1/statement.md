# 两张斜交圆柱面的 Section 应生成完整交线

半径为 10 和 5 的两个圆柱按公开脚本给出的轴系定位，在轴向参数 −35 到 35 之间取全周侧面。对这两张面求 Section 后，应得到六条截边，总长约 79.4278。沿每条截边采样时，点到任一圆柱面的最大距离应不超过 2e-7。用 `DRAWEXE -b -f public/reproduce.tcl` 可复现。

冻结任务：进入与本题面同目录的公开输入目录（即题面所在目录），运行 `DRAWEXE -b -f reproduce.tcl`。在题库源码的题目目录下则运行 `DRAWEXE -b -f public/reproduce.tcl`。
