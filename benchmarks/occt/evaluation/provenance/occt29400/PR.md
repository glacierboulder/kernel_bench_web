# General Fuse 对近端相交的样条边产生过短分段

两条输入边位于共同顶点的公差邻域。General Fuse 的求交阶段把不能再分割的短参数区间当成可分割区间，留下两个相互干涉的顶点。修复在生成分段之前检查可用参数范围。不以命令退出或普通形体验证作为唯一判据：结果可以通过 `checkshape`，却仍有顶点干涉。

- 自然父版：`8197951d7e2f9e8408f25a5329a6cbca8d172576`。[修复和上游测试](https://github.com/Open-Cascade-SAS/OCCT/commit/e25185fff00ab370800b0af074313ca0c728731b)
- 输入：[公开模型](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/bug29400_edges.brep)，Git blob `a4438c52ba9adace47affad7e9e47735355b43be`。沿三轴共同平移 (1, 2, -4) 和绕 Z 轴旋转 90° 构成两个邻域。
- 几何判据：3 个顶点、2 条边、总长 1.78839（绝对误差小于 0.00002），结果有效且无自干涉。正常对照为两条垂直横穿的直线段：5 个顶点、4 条边、总长 4，无自干涉。
- 逐例对照：[修复前](natural-B.txt) · [修复后](natural-F.txt)。公开命令为 `DRAWEXE -b -f reproduce.tcl`；在冻结目录执行。[公开原例输出](frozen-public-F.json)

三个触发输入在 B 均得到 4 个顶点、3 条边，总长 1.78841。普通形体验证通过，但 `bopcheck` 报 V/V 干涉。在 F 均得到 3 个顶点、2 条边，总长 1.78839，干涉消失。两版在横穿直线的正常对照上都生成 4 条边，总长 4。

对照题库 main `20515e0`、可见 PR #2 至 #7 和此前正选：与 #29322 的“扩大顶点公差后漏算边边求交”不同，这里已经找到交点，修复的是极短参数区间中相交顶点的识别与合并。

正式离线复评通过原例 1/1、邻域 2/2 和回归 1/1。[复评记录](round-offline.json)
