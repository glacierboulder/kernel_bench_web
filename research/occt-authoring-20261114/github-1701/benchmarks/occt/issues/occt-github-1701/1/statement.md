# 等半径圆角产生异常顶点容差

对 prefillet.brep 的第 6 条边做半径 1.3 的圆角。原版返回成功，但顶点容差约 4.83，后续布尔切割结果无效。原例允许明确失败。若返回成功，顶点容差应低于 0.01，按复现程序切割所得实体有效，切除体积为 100，误差小于 0.01。半径 1.299 和 1.301 两例必须成功并通过同样检查。

请修改锁定的 OCCT 8.0.1 源码。使用 OCCT 头文件和库编译 public/reproduce.cpp，运行时传入 public/inputs/prefillet.brep 与 public/original.txt。检查通过时程序输出 TEST_DONE。

提交针对锁定源码的 patch.diff 与 report.md，说明根因、修复和实际验证。评测输入和程序保持原样。
