# 相交实体执行布尔公共部分运算后丢失重叠体积

公开 BREP 是 OCCT 工单 #30760 的原始双实体输入。在 DRAW 中恢复模型，将两个直接子形状分别作为参数和工具，执行 `bfillds` 和 `bbop overlap 0`。基线给出空的公共部分，但两个实体确实发生体积重叠。

公共部分应为一个有效实体、14 个面，体积约为 0.000106046；交换两个输入不应改变这一结果。请修复布尔内核，不要改动输入、放宽容差或为该模型设置特例。

[原始模型（固定版本）](https://raw.githubusercontent.com/a-betenev/opencascade-dataset/12ec0ea9af6db153903fe0cf57ff5c4f30f66830/brep/bug30760_shapes.brep)

冻结任务：进入与本题面同目录的公开输入目录（即题面所在目录），运行 `DRAWEXE -b -f reproduce.tcl`。在题库源码的题目目录下则运行 `DRAWEXE -b -f public/reproduce.tcl`。
