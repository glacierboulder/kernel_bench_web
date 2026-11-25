# GH-1550 Coons 曲面切向回归

本次专项核对 `GeomFill_CoonsAlgPatch::D1U(U,V)` 和 `D1V(U,V)` 的有向三维切向。已知 `Value(U,V)` 边界塌缩继续单列为基线已有失败。它的旧回执及默认评分入口照原记录保留。[旧 Value 逐边证据](../rollout-v29/README.md)

## 源码锁和解析判据

在 ws01 使用 GCC 13.3、Release `-O3 -DNDEBUG` 和 `TKGeomAlgo`。锁定源码身份 `occt801-b8f597c67781-coons` 对应提交 `b8f597c677811d1f9f4d8a97f5ae2825c0353a42`，物化树 SHA-256 为 `26ed3f36926bb569ab8921398fea620ea10c80a2c4489ed42e8fcfb2981df8c5`。先核对归档无补丁构建的源码、缓存和库哈希。正式入口用同一锁定源码和仅新增说明文本的中性补丁重建，编译并发为 2。[无补丁运行身份](receipts/clean/process.json) · [中性补丁](../rollout-v21/neutral.diff)

| 工件 | 参数域 | 独立 `D1U` | 独立 `D1V` |
|---|---|---|---|
| 10×6 倾斜矩形，保留边的弧长参数 | `[0,10] × [0,6]` | `(0.6,0,0.8)` | `(0,1,0)` |
| 直边非平面双线性面，沿用登记形状和归一化边界 | `[0,1]²` | `(10,0,2−3v)` | `(0,10,1−3u)` |

第一组来自沿两个直边方向的仿射坐标。第二组四个角给出双线性表达式 `(10u,10v,2u+v−3uv)`，直接求导得到参照。程序核对四条边的实际参数范围、有向端点，再在每组 25 个含角点、边界和内部的参数位置读出两条切向。比较完整三维向量，误差上限沿用 **10⁻⁷**。解析参照直接来自输入几何，未用已知失败的 `Value` 做差分。验收范围限于这两类夹具和所列参数位置。[现场用例](../../../benchmarks/occt/evaluation/cases/version-regressions/1/coons-tangents.cxx)

## 对照如何生效

每组现场读取 50 条正常切向。用这些真实输出组成三组反例，分别交换 U/V、只反转 U、只反转 V。将交换和反转后的向量也写入 CSV，复核脚本直接重算三维误差并核实实际变换。两个夹具共保存 200 对向量，其中 50 对是原生结果，150 对是负对照。[无补丁现场记录](receipts/clean/gh1550-tangents.csv) · [无补丁逐项回执](receipts/clean/checkpoint.json)

## 正式现场回执

正式构建及评分用时 **461.065 秒**。两次构建各自实际生成的 CSV 逐字节一致，SHA-256 为 `2b78cdca8d9eb7f857f00d240bf641484e478ff2a9c93664c5583b810984b1bc`。正式运行记录 CMake 缓存和 7 个动态库的哈希。现场 CSV、构建指纹和编译命令各自留存，并由同次运行的哈希清单关联。[正式原始评分](receipts/formal/driver.json) · [现场 CSV](receipts/formal/gh1550-tangents.csv) · [构建指纹](receipts/formal/gh1550-build-sha256.txt) · [正式 CLI 回执](receipts/formal/cli.json)

| 实际对照 | 倾斜矩形 `D1U / D1V` 合格数 | 双线性面 `D1U / D1V` 合格数 | 判定 |
|---|---:|---:|---|
| 原生接口 | 25/25、25/25 | 25/25、25/25 | 通过 |
| 交换 U 和 V | 0/25、0/25 | 0/25、0/25 | 拒绝 |
| 仅反转 U | 0/25、25/25 | 0/25、25/25 | 拒绝 |
| 仅反转 V | 25/25、0/25 | 25/25、0/25 | 拒绝 |

正式运行的原生 100 条向量全部符合判据。倾斜矩形最大误差约 3.51×10⁻¹⁶，双线性面约 6.86×10⁻¹³。六个错向反例均拒绝。17 项框架测试通过。模型运行数和改变内核行为的补丁复评数均为 0。[独立复核与逐项结果](results.json) · [框架回执](receipts/framework-tests.txt)

## 最终分母与边界

显式选择的 `occt-github-1550-tangents-version-regression@1` 仅绑定 GH-1550 自己的锁定版本。全部 **37/37** 个锁定源码身份各有通用六项和至少一项正式校准的专项。通用共 222 项。按登记回归引用计，129 个引用中 **37 项校准通过、27 项校准未通过、65 项未执行**。不同构建配置按独立身份入账。这个结论覆盖每个锁定身份的最低验收范围。GH-1550 的 `Value` 边界失败、原默认评分、历史结果及十题 v3 均沿用原记录。[最终台账](ledger.json) · [逐版本清单](version-plan.json)

```bash
python3 -B research/kernel-regression-v1/rollout-v33/verify.py
python -m backend.reevaluate --patch "$PATCH" \
  --source-id occt801-b8f597c67781-coons \
  --suite-id occt-github-1550-tangents-version-regression --suite-version 1
```

下一步将各专项、台账和核验所需的最小证据整理成可审查改动，在干净检出中验证回执哈希及可选入口。
