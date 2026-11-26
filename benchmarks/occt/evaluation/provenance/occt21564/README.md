# [OCCT 21564] 两个平面相交时直线截边包含多余控制点

正式离线复评回执 `5bee8023d542262e`：原例 1/1、邻域 2/2、正常对照 1/1，技术通过，未调用模型。评测冻结摘要与公开 B/F 重演一致：`9c0e2c12634e1636e007c215586ce3c98398f48730efc3a80f18357afa9fc064`。

锁定自然父版 `7a324550c8cdbf0e55505e78d92c7233f68bc031` 与[上游修复](https://github.com/Open-Cascade-SAS/OCCT/commit/0cbfb9f15140fce08ac4fac39bb34ed0da69b0fa)。[原始 DRAW 测试](https://github.com/Open-Cascade-SAS/OCCT/blob/0cbfb9f15140fce08ac4fac39bb34ed0da69b0fa/tests/bugs/modalg_5/bug21564) 自建两面，不需下载模型。参考补丁只取自然 B→F 的 `src/` 修改，SHA-256 为 `d55fc878092ca8b0023e20a03f60d9507ed898b89255a2243ae5869dd437e5be`，不把上游测试或评测脚本当修复。

**缺陷位置。** 一张有界水平面用 B 样条表示后，与两张解析平面分别求交。对组边之前的 `bopcurves` 单独读数，两版都得到一条交线，但 B 的曲线为 4 次、101 极点、34 节点，F 为 1 次、2 极点、2 节点。所以上游差异已经发生在面面交线表示层，而不是边数或实体有效性。源码修改包括清理步进交线的冗余采样和调整逼近算法的分段判据；不声称每一个上游辅助修改都是触发原例所必需的。

| 输入与观测 | 自然父版 B | 修复版 F |
|---|---|---|
| 原始：竖直和倾斜刀面，各测普通/近似模式 | 4 次均 1 条有效边、101 极点 | 4 次均 1 条有效边、2 极点 |
| 两输入共同平移 (3,4,5) | 4 次均 101 极点 | 4 次均 2 极点 |
| 交换两个操作数 | 4 次均 101 极点 | 4 次均 2 极点 |
| 球半径 4 与赤道平面的曲线对照 | 1 条有效边，长 25.1327 | 1 条有效边，长 25.1327 |

三区分输入都要保持几何长度：竖直 20、倾斜约 22.36068，容差 0.001。冻结公开命令 `DRAWEXE -b -f reproduce.tcl` 在 B、F 的相同四组输入上分别得到 101 与 2 极点，边数、有效性、长度均正确。细节见同目录的 `frozen.json` 与 `frozen-{B,F}.log`；`assertion-{B,F}.log`、`faceface-{B,F}.log` 为独立阶段诊断。

**重新评测。** 本地预先导入锁定源码，运行 `python -B -m backend.reevaluate --patch reference.patch --source-id occt70-21564-b-7a324550c8cd --suite-id occt-21564-suite --suite-version 1`。对照 `source-import.json`、`result.json` 和冻结记录。Linux GCC 13、CMake、Tcl/Tk 8.6、`-O0 -DNDEBUG`；这一早期 OCCT 的 CMake 会在 Tcl 前缀下查找 Tk，需同时部署 libtcl8.6、libtk8.6 和 Tcl 的 init.tcl，且前缀对评测沙箱可见。未变更公共评分器或以预编译的几何内核代替正式构建。原例、两个邻域和正常对照分别独立计分。
