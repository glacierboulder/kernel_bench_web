# v4 十题交付摘要

记录时间：2026-10-27T16:52:44Z

- 正式 bundle：benchmark/occt-boolean-intersection-v4-10/
- 题目、group、suite：10/10/10；test checkpoint 和 scenario：40/40；冻结角色：60。
- 角色结果：10 个 original B geometry_fail，10 个 original F pass，20 个 neighborhood F pass，20 个 regression B/F pass。
- 旧 formal7 的 42 个角色按原矩阵、case、stdout/stderr SHA 逐项复用；没有重跑这 42 个几何角色。新 18 个角色包含 M30703、M33615 的 12 行、M29972 regression B/F 两行，以及 M29972 修正 snapshot 下的四行。
- 4 个 fail-closed 负控全部拒绝；真实框架隔离 SQLite 导入 10 项 PASS。
- 运行面文件扫描 135 项，外部绝对路径/runtime 路径命中 0，symlink 0；staging 到 formal10 的 218 个源文件 SHA 全匹配。
- M29972 只评分 section continuity。其独立 full upstream xdistcs 残差扫描的两个样本超过原始 2e-7；不宣称完整 upstream test 通过。
- M30703 的旋转/缩放备选不计为 required neighbor；M33615 只声明 BOP intersection 输出范围。
- 没有执行 fresh Agent patch/apply/build end-to-end，也没有第二台机器验证。
