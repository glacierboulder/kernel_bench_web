# 新增 OCCT 单题：布尔差集漏识别已分割的共端点边段

目标题库：glacierboulder/kernel_bench_web。仅一题，OCCT #27948 是原始模型工单，#29646 是对应的同一修复，不重复计数。

**根因。** B 的 `BOPAlgo_PaveFiller::ForceInterfEE` 以原始边对是否参与过第一遍 EE 干涉为跳过条件。两个端点被归入同域顶点后，仍可能需要重测其中的边段是否重合。第一遍见过两条原始边，并不表示这两个分割段已经属于同一公共块。F 改为按不同参数体、非退化边和公共块的实际状态决定是否测试。B 的切后实体可通过有效性检查，却带有多余的壳。只换 EE 实现可复原正确结果；只换同提交的 BuilderFace 分类实现不能。

这不同于题库 #29322 引入共端点强制 EE 检查：本题的自然 B **已经有该算法**，缺陷是其中的“原始边对已测过”过滤条件。两者 F、输入以及判别实验不同。

| 例 | B：线框/面/壳/实体；面积 mm²；体积 mm³ | F：同列 |
| --- | --- | --- |
| 原例 | 23/20/2/1；138.208；42.8584 | 19/17/1/1；135.137；40.573 |
| 共同平移 (3,-2,1) mm | 23/20/2/1；138.208；42.8584 | 19/17/1/1；135.137；40.573 |
| 共同绕 Z 轴旋转 17° | 23/20/2/1；138.208；42.8584 | 19/17/1/1；135.137；40.573 |
| 正常盒体差集 | 6/6/1/1；94；60 | 6/6/1/1；94；60 |

四例均要求有效形体、精确拓扑计数，面积和体积绝对误差各不超过 0.015 个相应单位。积分类 DRAW 命令请求的相对精度为 1e-6。另测同缩放 1.02 后 F 出现额外分段，拓扑判据不具该缩放不变性；该实验已记录但不计分。

- [B](https://github.com/Open-Cascade-SAS/OCCT/commit/4563472c1eb4a22cd84437d4eaaf7190b8bc4ed2)、[F](https://github.com/Open-Cascade-SAS/OCCT/commit/f8163956919390755b706b7d4a9f0731954bd232)、[DRAW](https://github.com/Open-Cascade-SAS/OCCT/blob/f8163956919390755b706b7d4a9f0731954bd232/tests/bugs/modalg_7/bug27948)。F 的直接父版为 B。
- [被切体](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/bug27948_a.brep)，SHA-256 `dfddc1c1d3076c048a854b65087d1f2c5f01660c845164675ef013a766cae9a0`。
- [刀具](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/bug27948_b.brep)，SHA-256 `a71726801157609e4b5e7986405431bf2c89675bd211d9970285ee91f6664438`。
- 正式流程：从锁定 B 导入干净源码，题库 `backend.reevaluate` 应用仅含生产源变更的参考补丁，从头构建并运行四个检查点。公开复现仅使用快照的 `visible/issue_27948` 及自然版 DRAW，在该目录运行 `DRAWEXE -b -f reproduce.tcl`。
