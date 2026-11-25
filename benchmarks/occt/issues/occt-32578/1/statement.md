# 用一组边切分曲面时遗漏分区或生成自交结果

在 DRAW 中读入公开的面和边集合。将面作为对象，逐条将边作为工具，设置布尔模糊公差为 0.01 后执行分割。输出应构成有效且无自交的面分区，面积约为 351.033 平方单位。按共享拓扑去重后，应有 646 个顶点、1234 条边、589 个环和 589 个面。

构建此历史版本需要 GCC 13、CMake、Tcl 8.6 和 FreeType 开发包。在评测部署使用的 Python 环境中激活虚拟环境后，从公开输入目录执行以下命令，再使用题目工具链运行原生构建和复评。

```sh
install -m 0755 cmake-occt32578 "${VIRTUAL_ENV:?activate the evaluation environment}/bin/cmake-occt32578"
export BENCH_CMAKE="$VIRTUAL_ENV/bin/cmake-occt32578"
```

启动器对 CMake 配置命令启用上游的 `USE_FREETYPE` 选项。题面和两个 BREP 输入均与公开脚本放在同一冻结目录中。

冻结任务：进入与本题面同目录的公开输入目录（即题面所在目录），运行 `DRAWEXE -b -f reproduce.tcl`。在题库源码的题目目录下则运行 `DRAWEXE -b -f public/reproduce.tcl`。
