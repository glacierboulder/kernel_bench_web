# 圆角端部求交从错误面参数出发

在 model.brep 的第 12 条边做半径 1 的圆角。原版报告成功，顶点容差约 93.15，布尔检查有 63 个缺陷。端部没有参数曲线时，求交起点应与共同点一致。给定原例和第二个模型必须成功构造，结果有效、布尔检查无缺陷，最大顶点容差低于 0.01。正常圆角继续成功。

请修改锁定的 OCCT 8.0.1 源码。使用 OCCT 头文件和库编译 public/reproduce.cpp，运行时传入 public/inputs/model.brep 与 public/original.txt。检查通过时程序输出 TEST_DONE。

提交针对锁定源码的 patch.diff 与 report.md，说明根因、修复和实际验证。评测输入和程序保持原样。
