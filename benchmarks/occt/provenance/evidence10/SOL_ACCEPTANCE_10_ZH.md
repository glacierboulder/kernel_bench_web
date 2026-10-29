# Sol 验收记录：OCCT Boolean 求交 v4 十题

依据本阶段审阅结论，接受当前十题的范围、冻结几何回放和隔离导入证据。

- 10 道 single-issue 题目、40 个 test checkpoint、40 个 scenario、60 个冻结角色；结果为 10 个 original B geometry_fail 和 50 个 geometry_pass。
- M30703 按低层 surface-surface 求交判据评分；M29972 仅按 section continuity 评分；M33615 按 BOP 求交输出判据评分。
- M29972 完整 upstream xdistcs 面残差诊断仍未通过其原始 2e-7 阈值；不声称完整 upstream 脚本全部通过。M30703 未通过的旋转/缩放备选不计入 required tests。
- 四项 fail-closed 负控全部拒绝；十项任务已导入新的隔离 SQLite 数据库。
- 原先明确排除的五个 identity 未重复；既有 formal7 目录与原有 42 个角色证据保持不变。新增三题的来源及迁入依据随证据包保存。
- Fresh Agent patch/apply/build 端到端和第二台机器验证尚未完成，不在本次验收范围内。

本记录接受的是上述题目与几何证据范围，不代表未执行的 Agent 端到端或跨机器验证通过。
