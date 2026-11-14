# 双边圆角报告成功但产生无效线框

对 bar_plate_r1.6.brep 的第 11、21 条边同时做半径 1.3 的圆角。原版报告完成却返回无效形状。修复后应得到通过 BRepCheck_Analyzer 的结果，或明确返回未完成。两组单边圆角与杆半径 1.5 的双边圆角应继续成功并返回有效形状。额外布尔诊断用于分析，正常对照在原版上已有小边等报告。

请修改锁定的 OCCT 8.0.1 源码。使用 OCCT 头文件和库编译 public/reproduce.cpp，运行时传入 public/inputs/bar_plate_r1.6.brep 与 public/original.txt。检查通过时程序输出 TEST_DONE。

提交针对锁定源码的 patch.diff 与 report.md，说明根因、修复和实际验证。评测输入和程序保持原样。
