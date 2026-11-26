# 修复带种子面面求交后未按修剪面域截断的边

取同一原始 BREP 中的前两个面，运行真实的布尔截交，不使用新增的 DRAW 选项。B 的 IntTools_FaceFace::MakeCurve 在收到初始交点列表时跳过交线构造器；IntPatch_WLineTool 还可能在保留采样点时覆盖顶点标记。F 保留顶点身份，并使有种子时的交线也接受面域裁剪。参考补丁只含这两处内核改动，不含 BOPTest 的诊断命令变更。两处未进一步独立拆分归因。

| 输入 | B 顶点/边/总长 | F 顶点/边/总长 |
| --- | --- | --- |
| M3 原例 | 5 / 5 / 22.6867 | 3 / 2 / 22.2576 |
| 同移 (2, −3, 1) | 5 / 5 / 22.6868 | 3 / 2 / 22.2576 |
| 交换两面，交换两侧 UV 域 | 7 / 9 / 22.9966 | 3 / 2 / 22.2576 |
| 两张垂直的有限平面 | 2 / 1 / 6 | 2 / 1 / 6 |

长度用模型长度单位。三触发例要求结果有效，2 边、3 点，长度 22.2575 ± 0.001。正常例长度 6，容差 0.00001。原始输入 [GEN758_nofog.rle](https://github.com/a-betenev/opencascade-dataset/blob/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep/GEN758_nofog.rle)，SHA-256 `4a9b6427a313a375dcdbf9424fe7279ebef04dcd80cc6122eaddc0eeb871e55c`。[自然 B](https://github.com/Open-Cascade-SAS/OCCT/commit/c9e1d810abfa9e49255b7b9ade86006567af7a9c)、[修复 F](https://github.com/Open-Cascade-SAS/OCCT/commit/47e3009da9a2d86bdcf01f166e552adeee57af12)、[原始 DRAW M3](https://github.com/Open-Cascade-SAS/OCCT/blob/47e3009da9a2d86bdcf01f166e552adeee57af12/tests/boolean/bsection/M3)。

同一脚本提到的 #26777 不另计。旧未完成草稿 #28802 虽也用此模型，研究的是后续版本里生成边的逼近容差；其补丁前后始终是 2 边、22.2576，未登记入库。本题的修复提交不同，且在自然父版产生可测的多余截边。第一轮 #23214 处理的是二维曲线逼近越界后的回退，模型及修复均不同。
