# 圆角支撑面步进交线错误识别边界

在 `GeomInt_IntSS_1.cxx::DecompositionOfWLine` 分割步进交线时，B 取底层 Geom_Surface 的 Bounds 判定临近点是不是 UV 边界点。底层曲面范围不等于传入适配器的裁剪范围；旧判定会给后续逼近提供错误的交线段端部。F 唯一的生产改动是改读适配器的 First/Last U/VParameter。此处以实际源码为准，不能把两个方向说反。

对原始模型第 15 条边做半径 9 mm 的有理圆角，保留历史 DRAW 的 SetParams 与连续性。触发例的共同判据：结果有效、14 面、面积为 197055.036 ± 0.2 mm²、全形子形最大容差不超过 0.001 mm。全形上界包含上游第 21 边及其顶点，防止旋转后编号变化使断言漏测；原例还直接量了该边，B 为 310.821196 mm，F 为 0.0000001 mm。

| 输入 | B：最大容差 mm / 有效性 | F：最大容差 mm / 有效性 |
| --- | --- | --- |
| 原例 | 310.821196 / 否 | 0.0001 / 是 |
| 沿 X 平移 10 mm | 310.820902 / 否 | 0.0001 / 是 |
| 绕 (1,2,3) 轴旋转 15° | 311.485729 / 是 | 0.0001 / 是 |
| 边长 100 mm 盒体，半径 9 mm | 0.0000001 / 是 | 0.0000001 / 是 |

正常盒体两版均 7 面，面积 59578.9511966 mm²，与解析值一致。每例的面积与可读几何量见自然运行日志；B 旋转例证明只检查有效性不足。探索过的斜向平移、微调半径及四分之一圈旋转并非都能分辨 B/F，未纳入计分。

来源：[B](https://github.com/Open-Cascade-SAS/OCCT/commit/2a78ec6a074716322d15275a771c5c1105fa4057)、[F](https://github.com/Open-Cascade-SAS/OCCT/commit/31cf9c5f7dd2cdc19db053ec246f32ac61f7a09a)、[DRAW](https://github.com/Open-Cascade-SAS/OCCT/blob/31cf9c5f7dd2cdc19db053ec246f32ac61f7a09a/tests/bugs/modalg_5/bug25199)、[原例调用的 bug615 脚本](https://github.com/Open-Cascade-SAS/OCCT/blob/31cf9c5f7dd2cdc19db053ec246f32ac61f7a09a/tests/bugs/modalg_3/bug615)、[固定 OCC615.brep](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/OCC615.brep)，SHA-256 `d6329e221c2e1b5462cbac3129f2f89605c64d100fcb7178c7bf6ffbeed7bdc2`。
