# 抛物线与平面的两个布尔截点合并成一个

公开输入用二次 Bézier 边表示抛物线 z = x²/100 − 0.005，y = 0，并将边的容差设为 0.01。与 z = 0 的矩形面求截，应该得到两个独立顶点，横坐标为 ±√0.5，纵坐标和高度均为零。

在题目目录运行 `DRAWEXE -b -f public/reproduce.tcl` 可查看截点数与各点坐标。

冻结任务：进入与本题面同目录的公开输入目录（即题面所在目录），运行 `DRAWEXE -b -f reproduce.tcl`。在题库源码的题目目录下则运行 `DRAWEXE -b -f public/reproduce.tcl`。
