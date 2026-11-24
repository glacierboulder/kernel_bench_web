# 相交圆柱的 General Fuse 丢失分割区域

两个相交圆柱经 General Fuse 后，旧版可能遗漏一个分割区域，即便输出通过形状有效性检查。修复分割，使公开复现得到 3 个实体、10 个面、11 条边、5 个顶点及约 154518 的总面积。

在冻结题面所在目录运行 `DRAWEXE -b -f reproduce.tcl`。在题库源码的题目目录运行 `DRAWEXE -b -f public/reproduce.tcl`。
