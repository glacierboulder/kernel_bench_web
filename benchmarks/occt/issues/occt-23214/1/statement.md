# 面与壳求截时两段交边的总长错误

用随题的 `OCC23214-face_1188.brep` 和 `OCC23214-shell_for_line_1188.brep` 做布尔 Section。旧内核会生成两条拓扑有效的边，实际总长约 3.58339。请修复求交，使交边位于指定的面域内。

公开输入的正确结果是一个复合形，含 4 个不同顶点、2 条边，不含线框和面，且通过 BRep 有效性检查。两边总长应为 2.94086，绝对误差不超过 0.0001。

在题面旁的冻结公开目录或仓库题目目录的 `public/` 运行以下命令。构建需要 Linux x86-64、GCC、Ninja、Python 3、GNU binutils、dpkg-deb、xz 和 Tcl 开发头文件。其余生成依赖均已随题提供。

```sh
bash public-build.sh /path/to/occt /tmp/occt-23214-build
bash public-replay.sh /tmp/occt-23214-build
```
