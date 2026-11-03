# 圆柱求交产生错误曲线

对给定两圆柱执行面面求交及实体 Section。基线会产生数量和几何位置错误的交线，后续 Section 也需保持闭合。请修复源码，验证刚体变换、输入交换与无交情况，提交 `patch.diff` 和 `report.md`。

在 DRAW 中加载 `public/reproduce.tcl`，公开输入随题提供。
