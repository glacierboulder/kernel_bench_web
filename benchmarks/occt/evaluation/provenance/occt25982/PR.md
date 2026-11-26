# 新增 OCCT #25982 镜像自由曲面 General Fuse 回归题

本题以公开的 BREP 原件与它关于平面 `x=0` 的镜像作为输入，从两者各取第 4 个面。General Fuse 需要为交边构造面上的参数曲线。历史版本在底层曲面上投影时没有约束到实际裁剪面域，导致结果丢失一个面。[上游修复](https://github.com/Open-Cascade-SAS/OCCT/commit/fd372378a118c855b8713bbce40f81d0434d187a)

| 检查点 | 自然父版 1804bb99 | 修复版 fd372378 |
| --- | --- | --- |
| 原例、交换操作数、同时平移 | 每例 5 顶点、7 边、2 线框、1 面，面积 152.61359155 | 每例 6 顶点、11 边、4 线框、2 面，面积 306.28534224 |
| 普通对照，两张分离矩形面 | 8 顶点、8 边、2 线框、2 面，面积 4 | 同左 |

正式 `manifest-suite-v1` 复评从经验证的 Git 父版应用三处生产文件的参考补丁，重新生成 CDL 头文件并编译，原例 1/1、邻域 2/2、对照 1/1 通过。该运行使用离线参考补丁模式，未调用模型，也未提供模型提交报告。冻结后的公开 C++ 原例在自然 B 与 F 上分别返回 1 和 0。[复评记录](round-offline.json) · [公开 B](frozen-public-B.txt) · [公开 F](frozen-public-F.txt)

构建使用可离线解包的 WOK 工具链，SDK 包含随附版权声明的 Debian 原包和上游生成模板。几何库均从待测内核源码和该版本的 CDL 重新构建。上游面积判据的相对容差为 1%。[构建来源](toolchain-source/SDK-SOURCES.md) · [原始测试](https://github.com/Open-Cascade-SAS/OCCT/blob/fd372378a118c855b8713bbce40f81d0434d187a/tests/bugs/modalg_5/bug25982)
