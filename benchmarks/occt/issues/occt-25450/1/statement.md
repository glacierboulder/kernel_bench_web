# 有效形体作布尔差后丢失边界面积

读入公开模型 `OCC497e.brep` 作为被切对象、`OCC497f.brep` 作为工具。按历史 DRAW 的 `bcut` 入口先执行干涉计算，再执行 `BRepAlgoAPI_Cut`。对给定参数，结果的边界表面积应约为 2471.48；操作返回完成不代表结果几何完整。

修复几何内核，使该差集恢复预期边界表面积；不要依赖模型在世界坐标系中的位置或朝向。合法的贯穿切割仍应保留应有的面和实体。不要修改输入、检查程序或期望值。

在 Linux x86-64 上，从本题的公开材料目录运行下列命令。`OCCT_SOURCE` 指向待测源码树；`BUILD` 指向一个新的空目录。使用 GCC、Ninja、Python 3 和包内提供的历史 CDL 生成器，不依赖系统安装的 OCCT。

```bash
bash public-build.sh "$OCCT_SOURCE" "$BUILD"
bash public-replay.sh "$BUILD"
```

观察面积和拓扑数量，不要只看布尔运算的退出状态。几何未达标时程序输出 `verdict=FAIL`、退出 1；通过时输出 `verdict=PASS`、退出 0。
