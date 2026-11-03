# 二十道 OCCT 单 issue 题目准入报告

已完成 20 道单 issue 题目的构造、资格校准、注册及冻结回放。分支为 `codex/occt-single20-20261102`，仓库基线为 `c5184df5e161c72cfa389249a8b052efe1b87cf6`。本轮按用户提供的 `benchmark-authoring.md` 执行。

## 验收结果

| 检查类别 | B 基线 | F 正参考 |
| --- | --- | --- |
| 原例，20 条 | 20 FAIL | 20 PASS |
| 邻域，40 条 | 3 PASS，37 FAIL | 40 PASS |
| 回归，20 条 | 20 PASS | 20 PASS |

160 条冻结检查均完成执行。20 个原例均形成真实缺陷差分，80 条 F 必需检查全部通过。另有 61 个人为错误输出负对照在准确 F 上被拒绝。每题包含一个原例、两个独立邻域和一个适用回归，作答预算均为 7200 秒。

每次回放均核验锁定源码缓存、调用共享公开构建入口，并使用冻结的共享适配器和严格断言契约。40 份 B/F 快照的源码、评分资产和构建后库身份均有记录，完整本地快照已再次验算。新增题目全部采用 `kind=single`，每个任务只有一个 issue member。

清单共包含 54 个 issue versions、42 个任务和 42 个 suite。原有 catalog 身份与 10 个 source lock 条目的保留校验通过。规范 issue 身份去重及输入字节去重均通过，22 份新公开几何输入与 156 份原注册公开材料及声明依赖之间未发现相同文件。M27221 因复用既有 M27252 输入和修复覆盖而被排除。

完整任务、source commit、树哈希、suite、工具链及逐检查点结果见 [题目映射](../../../research/occt-single20-authoring-20261102/registered-tasks.json) 和 [逐项矩阵](../../../research/occt-single20-authoring-20261102/qualification-matrix.json)。

## 题目与参考身份

| Issue | 题目 | B commit | F commit |
| --- | --- | --- | --- |
| 24097 | 短截交曲线被截断 | `5163f4671951` | `1511c7e90f1a` |
| 24313 | OCCT M24313 · 线性拉伸曲面与平面的双母线求交 | `78b6b239841f` | `1511c7e90f1a` |
| 24418 | OCCT M24418 · 圆环面与圆锥求交精度 | `1511c7e90f1a` | `cfde7eebb37b` |
| 24429 | 圆柱与圆环面求交异常 | `1511c7e90f1a` | `cfde7eebb37b` |
| 25102 | 复杂面截交遗漏部分交线 | `5163f4671951` | `1511c7e90f1a` |
| 25111 | 圆锥与圆环面的截交曲线缺失 | `029311e00f28` | `5163f4671951` |
| 25342 | Section 返回错误的边数 | `5163f4671951` | `1511c7e90f1a` |
| 25542 | 圆柱与圆锥 Common 丢失结果 | `1511c7e90f1a` | `a016080bf673` |
| 25818 | OCCT M25818 · 无界平面求交的完整直线 | `32ab8bfc4f09` | `1511c7e90f1a` |
| 26243 | 带圆角模型的 Common 运算失败 | `5163f4671951` | `2199db4a362b` |
| 26310 | 圆柱求交产生错误曲线 | `ea80ac2f61af` | `a016080bf673` |
| 26776 | 偏置曲面与拉伸面截交不完整 | `1511c7e90f1a` | `cfde7eebb37b` |
| 26796 | 近接触盒体的 General Fuse 分块错误 | `6435b9c7fafd` | `1511c7e90f1a` |
| 26910 | 直线与圆弧 General Fuse 漏掉近交点 | `6435b9c7fafd` | `1511c7e90f1a` |
| 27227 | 正交圆环交线未延伸至边界 | `cfde7eebb37b` | `a016080bf673` |
| 28195 | 复杂实体 Common 丢失公共体 | `1511c7e90f1a` | `cfde7eebb37b` |
| 28216 | 薄壁锥形实体与曲面 Common 为空 | `1511c7e90f1a` | `cfde7eebb37b` |
| 28388 | 薄壁圆柱实体与曲面 Common 为空 | `1511c7e90f1a` | `cfde7eebb37b` |
| 33639 | 圆锥尖点接触圆环时 Cut 失效 | `a016080bf673` | `1511c7e90f1a`，历史工作版 |
| github-1543 | 螺旋工具穿过端面时 Boolean Cut 未移除材料 | `a016080bf673` | `d3c3366e548f` |

其中四份 B 为明确的派生基线，分别对应 M25818、M24313、M25111 和 M26310。其余 B 使用准确自然提交。M26243 与 GitHub #1543 的 F 使用有来源的派生参考，其余正参考为准确自然提交。

## 几何规则及互补关系

- M25818、M24313 检查无界参数域和不同母线，补充既有有限求交题的覆盖。
- M24418、M24429、M25111、M27227 根据解析支持方程、端点连接及分支见证点验收圆锥、圆环与圆柱求交。M27227 直接覆盖内外侧接缝端点。
- M24097 的双三次曲面与线性拉伸面由独立 de Boor 求值和 Y/Z 方程求解得到正参考。Bezier 导数控制点界限支持整个输入范围内的唯一性，独立长度约为 `0.125055907400858`，长度与见证点距离限为 `1e-6`。上游写出的 `0.125` 保留为近似描述。
- M26310 通过输入圆柱的世界坐标轴和半径计算真实支持误差，限值为 `1e-6`。曲线数量和实体 Section 的闭合性另行检查，报告容差单独保留。
- M26910 检查近交点、四条拆分边、交点度数和长度保持，扩展到 edge/edge 相交及参数拆分。
- M26796 用解析楔体体积、面积和质心检查 General Fuse 分块，提供与既有 544 同域合并题互补的拓扑装配问题。
- M26243、M25542、M28195、M28216、M28388 覆盖实体 Common 与面/薄壁实体裁剪。判据包含有效性、几何量、输入分类或解析区域归属及裁掉区域见证点。
- M25102、M25342 检查复杂 Section 的完整性，采用上游明确的长度、边数和端点图契约及错误输出校准。
- GitHub #1543、M33639 检查扫掠或奇点相关 Boolean Cut，结合独立体积分、有效性及保留/移除位置分类。

M25542 与既有 M29807 有修复家族关联，M28216 与 M28388 也存在机制相关性。映射和来源记录保留了这些关联。题目数量与独立机制数量分别解释。

## 参考与测量边界

M33639 的 B 为 OCCT 7.9.3，F 采用经核验的较早自然工作版本 `1511c7e90f1a`。正几何由独立截面积积分推导，体积约为 `879203614.534149`，Gauss 阶数 64、128、256 的结果差异小于 `1e-6` 体积单位。预先固定的体积限为 `1.0`，按尺度立方变化。较早的 2015-08 候选在该规则下失败。该选择提供几何正对照，agent 的提交仍应用于锁定的 7.9.3 B。

GitHub #1543 参考来自固定 PR head `850d86c592896a8b35edebb004a57f405b6d27c7` 的源码移植，归档时该 PR 尚未合并。输入按上游原始 C++ 构造导出并通过合法性检查，来源及生成器均保留。[参考 PR](https://github.com/Open-Cascade-SAS/OCCT/pull/1544)

M24418 的所选 F 直接父提交也通过程序化原例，唯一因果修复提交仍未定位。M26243 的面积绝对限 0.5 为作者选定的严格判据，上游 `checkprops` 默认相对 epsilon 为 `1e-4`。M25342 的主要金标准为上游明确的四条结果边，精确长度 gold 尚未独立建立。

有限支持采样、见证点、分类网格与数值积分只支持所声明的范围。GProp、BRepCheck、BRepClass 和距离测量与被测算法共用部分 OCCT 基础设施。连续域的认证误差界仍属于覆盖边界。

## 输入合法性与原型排除

恢复输入核对了固定数据集 commit 的 Git blob 和 SHA256。拓扑形状使用 BRepCheck，解析表面题核对构造参数和定义域。早期五题另在准确 B/F 上补跑了十次输入合法性检查，全部通过。独立推导脚本、C++ 输入生成器及其结果身份随 provenance 保存。

原型错误与失败参考使用独立 job label 留档，包括 DRAW 变量覆盖、受保护变量命名、执行副本同步遗漏、无界支持面被误用作健康控制参数域、有限面距离被误用作支持面残差，以及近似显示值被误当精确 gold。后续检查绑定输入和 helper 的 SHA256，运行前核对复制后的快照。

| 未准入候选 | 状态与原因 |
| --- | --- |
| M27221 | EXCLUDED，与既有 M27252 重复覆盖 |
| M25890 | INCONCLUSIVE，较新自然参考在固定平移邻域中丢失全部曲线 |
| GitHub #1610 | INCONCLUSIVE，候选补丁和较早自然参考都未通过刚体邻域 |
| M28274 | INCONCLUSIVE，剥离无效网格缓存后的合法输入在所测 B/F 均通过，缺陷未复现 |
| M31850 | INCONCLUSIVE，恢复原共享 PaveFiller 调用入口后所测 B/F 均通过 |

其余候选的审查状态见 [候选决策](../../../research/occt-single20-authoring-20261102/candidate-decisions.json)。未准入原型保存在研究目录，完整运行输入快照归档保存。

## 实现与正常入口验证

共享构建增加 `adm/cmake/version.cmake` 版本识别，以支持配置时生成 `Standard_Version.hxx` 的源码版本。新题复用共享 OCCT runtime。新增 `scripts/prepare_single20_source.py`，从已有上游 Git 对象恢复自然或派生基线，并同时核验准确 commit、Git tree 和物化树哈希。

Linux 完整依赖环境执行了 24 项相关单元测试，22 项通过。2 项 NG-04R 历史缓存相关检查因相应缓存未准备而跳过。20 道新题的 160 条几何回放全部执行。独立数据库导入及再次导入均成功，确认 20 个新任务可注册且导入幂等。Mac 系统 Python 缺依赖、Linux 初期副本缺文件造成的验证失败另有记录，最终结果来自完整 Linux 副本。

四份新派生基线及一份自然基线通过可移植准备入口重建。以下示例中的目录由执行者指定，`OCCT_GIT` 需包含对应自然 origin commit。

```bash
export BENCHMARK_ROOT="$FRAMEWORK_ROOT/benchmarks/occt"
export BENCH_CACHE_DIR="$EXPERIMENT_ROOT/cache"
python scripts/prepare_single20_source.py "$SOURCE_ID"   --upstream-repo "$OCCT_GIT" --destination "$PREPARED_SOURCE"
python -m backend.source_cache "$SOURCE_ID" --from-dir "$PREPARED_SOURCE"
python -m backend.catalog --root "$BENCHMARK_ROOT" --json
```

## 证据入口

[逐项矩阵](../../../research/occt-single20-authoring-20261102/qualification-matrix.json) 关联每条 B/F 检查的 source、snapshot、二进制身份及原始 result/log 路径。各题 `evaluation/provenance/single20/<issue>/qualification.json` 保存准入结论及负对照记录。各题 `evidence.json` 内嵌可直接审阅的冻结结果和负对照日志。矩阵中的 `result_path` 为归档成员路径，框架验证记录单独保存在研究目录。

完整输入、评分快照和原始构建日志保存于 [证据归档](../../../research/occt-single20-authoring-20261102/evidence/occt-single20-evidence-20261103.tar.gz)，使用目录内相对硬链接去重。归档 SHA256、文件数及恢复方式见 [归档清单](../../../research/occt-single20-authoring-20261102/evidence-archive.json)。解包后可运行 `tools/finalize_qualification.py --evidence-root <解包目录>/jobs` 重新核对快照和当前规则。

本轮完成题目作者资格验证，受测 Agent 运行数为 0。
