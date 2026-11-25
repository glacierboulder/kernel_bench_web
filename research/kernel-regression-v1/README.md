# OCCT 按锁定源码身份的回归验收

本次交付为每个锁定源码身份提供六项通用检查的记录及至少一项已校准的登记专项。首批冻结的 37 个身份全部满足这项门槛，共 222 项通用检查。该批 129 个登记回归引用中，37 项通过校准、27 项未通过校准、65 项未执行。当前主分支新增的 18 个身份及其回归引用待纳入后续校准，当前库覆盖为 37/55。按身份统计时，同一提交的不同工具链或构建范围分别计入。专项成绩适用于各自清单中的几何、调用路径和判据。[最终台账](rollout-v33/ledger.json) · [逐版本索引](rollout-v33/versions.md)

## 复核

在含两个基线提交对象的干净检出中，用 Python 3.11 和仓库依赖执行：

```bash
python -m pip install -r requirements.txt
python -B research/kernel-regression-v1/verify_review.py
python -B research/kernel-regression-v1/rollout-v33/verify.py
python -B research/kernel-regression-v1/make_plan.py --check
python -B -m unittest discover -s tests -p 'test_catalog_contract.py'
```

检查执行真实的套件查询和源码身份选择，核对 Git 中证据文件、原始回执及评分资产的 SHA-256。并与 GitHub `main` 锁定提交和本地准备基线逐字节检查题组定义和默认评分材料。这些检查可离线执行。核对说明中的历史实现运行分为完整 CLI、隔离单项执行器及冻结对照，证据链沿用原回执，完整 CLI 数仅代表相应归档。复核回执哈希无需在本机重建 OCCT。[证据清单](review-evidence.json) · [最终专项实例](rollout-v33/README.md)

此分支以 `df89204` 为准备基线，已同步仓库 `main` 的 `3d50620`。向 `main` 比较时会包含三笔此前的 Common 可选扩展提交。回归验收包括 26 个新增可选专项、源码身份台账及其复核证据。冻结清单由 rollout-v33 内的登记快照重建，用于在新增题目后复核原来的 37 个身份。

## 使用可选专项

在具备该身份的验证源码缓存和对应工具链的 Linux 评测环境中，提供实际补丁及明确的专项版本。例如：

```bash
python -m backend.reevaluate --patch "$PATCH" \
  --source-id occt801-b8f597c67781-coons \
  --suite-id occt-github-1550-tangents-version-regression --suite-version 1
```

同一源码身份上的 `Value` 边界塌缩仍属于基线已有失败，切向专项仅验收 `D1U` 和 `D1V`。[边界失败证据](rollout-v29/README.md)
