# Sol 逐题正式验收记录：OCCT Boolean 几何求交 v4

验收日期：2026-10-27 UTC

Sol 已审阅并接受 7 个 single issue 题目：M32721、M32942、M31404、M31470、M32470、M32502、M33244。当前 web catalog 的 21 个 canonical identity 与 v4 题目重合数为 0。M32470、M32502、M33244 是经用户许可并逐题范围审阅后从 v3 迁入；其余 v3 identity 未迁入。

## 验收证据

- 7 issues / 7 groups / 7 suites；28 tests / 28 input scenarios；42 个冻结角色运行全部符合预期。
- 7 个 original 为 B geometry_fail / F geometry_pass；14 个 neighborhood 为 F geometry_pass；14 个 regression 为 B/F geometry_pass。
- 负控 4/4 拒绝；隔离 runtime SQLite 导入 7/7 tasks，未触及生产或共享数据库。
- 正式 bundle 的实际 catalog validator 返回 Valid catalog: issues=7, groups=7, suites=7。
- 完整矩阵、stdout/stderr、负控、隔离导入收据、scope 批准、迁入来源映射和 SHA 清单见本目录。

## 未验证边界

十题目标仍未完成，尚差 3 个新 canonical identity。没有进行 fresh Agent patch/apply/build 端到端，也没有第二台机器验证。WOK 历史路线仍缺 csh 依赖许可；本阶段没有下载或安装 csh，也没有继续 WOK 生成路线。
