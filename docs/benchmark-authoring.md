# OCCT 单 issue 优先的题目构造与验收指南

本文件是 OCCT 题库作者的唯一主指导，涵盖公开问题整理、候选筛选、测试构造、清单格式、可信评测、版本维护和正式准入。默认构造和准入单位是一个独立 issue version；合格单题可直接作为独立 catalog task。多 issue 组合只是有明确联合评测理由时的可选扩展，当前五组三成员题组只是既有实例，不是新题的模板或配额。网页目前没有题目编辑器；题目通过版本化文件维护。可复制的最小 bundle 示例见 [benchmark-example](benchmark-example/)。

单 issue 不需要与其他问题相似、不要求加入组合题，也不受组间重合率或成员相似度门槛限制。测试规模按问题复杂度扩展，但邻域覆盖遵循现有通过集的设计基线：每个 issue version 至少有多个独立 neighborhood test/checkpoint，参照现有每个 issue version 的 2–3 条设计；不把这个范围改成“恰好 3 条”。一个 test 可覆盖多个 scenario，但不能把一个 checkpoint 中的多个 scenario 记成多个 test。多 issue 的额外约束仅在作者选择组合题时适用。

本指南分开定义两件事：作者提交的题目材料何时达到准入条件，以及未来 Agent 补丁何时通过正式评测。清单校验、静态文件存在、成功构建或无崩溃都不是几何通过证据。

## 目录

- [使用说明与验收边界](#使用说明与验收边界)
- [端到端构造流程](#端到端构造流程)
- [作者准入与 Agent patch 通过标准](#作者准入与-agent-patch-通过标准)
- [多维邻域设计](#多维邻域设计)
- [Oracle 校准与负对照](#oracle-校准与负对照)
- [清单格式与目录结构](#清单格式与目录结构)
- [版本与稳定身份](#版本与稳定身份)
- [常用命令与运行顺序](#常用命令与运行顺序)
- [当前五组磁盘快照](#当前五组磁盘快照)
- [现有示例与证据链接](#现有示例与证据链接)

## 使用说明与验收边界

- 本指南只规定作者构造和验收题目的方式，不更改当前 catalog、source lock、evaluator 或数据库。
- 题目数据以当前 bundle 的 catalog、issue、group、suite 清单为准。字段边界由 [JSON schemas](../benchmarks/occt/schemas/) 和 [backend.catalog](../backend/catalog.py) 共同定义；schema 文件描述清单结构，validator 还会核对跨文件引用、路径、源码和 runner 兼容性。
- 新题库沿用当前版本化 catalog 路线和稳定 ID。单 issue 用 kind=single、恰好一个 member 的 group manifest，可通过现有 validator 和 worker catalog dispatcher 正常导入、排队和评测，无需改代码。已有五个新组及七个 legacy 组保持原有 group、suite、issue 和 source identity；不要照搬旧 Part2 目录结构或自行改名。
- 不存在单题必须与其他 issue 相似、必须组成三题组、组间 overlap ratio 达标或复用历史 Part2 比例的全局门槛。多 issue 合组的 manifest/source 兼容限制见[清单格式与目录结构](#清单格式与目录结构)。
- 运行结果必须保留证据边界。静态存在只说明文件被清单引用；catalog 校验只说明格式和引用关系成立；source cache 校验只说明源码身份匹配；只有可信 geometry oracle 实际运行并给出几何判据，才形成几何通过或失败证据。

## 端到端构造流程

### 1. 收集公开问题与来源证据

每个候选先按一个可追溯的上游问题独立整理和判断，不需要先找到相似 issue 或凑成多题组。整理公开 issue、上游讨论、复现材料、相关源码提交和修复讨论，并保留可供复核的链接或归档来源。明确记录：

- 上游项目、ticket/issue ID、标题、报告时间和可访问的公开来源。
- 复现操作、输入文件及其来源；原始报告给出的预期与实际观测要分开记录。
- 可能的修复提交、源码 commit 和补丁；注明它们是自然后续提交、单问题参考补丁，还是经说明生成的派生版本。
- 证据缺口：例如输入未恢复、参考 commit 不可用、现象只在某运行环境出现，或原报告没有精确几何期望。

不要把 issue 描述直接等同于已复现的几何失败。候选可保留为 proposed、unknown 或 tentative，并写明下一步需要的证据。

### 2. 标注有证据支持的最早失败大阶段

用最早有直接证据支持的阶段组织候选：

- 几何表示
- 几何求交
- 参数域拆分
- 拓扑装配
- 分类
- 生命周期

标注应引用可复核证据，例如复现日志中的几何结果、上游修复 diff 或明确的中间表示差异。无法判定时填写 unknown 或 tentative，不要为了让分类表完整而猜测。细机制可以作为注释，不能变成额外 admission 门槛，也不能替代大阶段证据。若同一问题跨阶段，记录“最早已证实阶段”并附上后续影响。

### 3. 筛选候选并固定 B/F 身份

先按上游问题的规范身份去重，再判断它是否适合作为题目。为每个 issue version 明确：

- B：锁定的修复前基线。记录稳定 source_id、完整 commit 和 materialized source tree SHA-256。
- F：修复参考。优先采用能复核的自然后续修复 commit；也可采用有来源、补丁哈希和推导步骤的明确派生参考。
- agent：未来提交的 patch.diff，由可信 evaluator 在相同锁定基线和指定 suite 上评测。

source lock 的 source_id 绑定 Agent 的 B baseline。F 可以是另一个经过验证的自然后续 commit，也可以是可信 reference.patch/派生树；将 F 的身份、推导过程和 hash 放入可信 provenance/evidence，不要为了让测试通过而把 Agent 的 B lock 换成 F。如果 F 是自然后续 commit，就按那个 commit 原样验证；它可以同时包含多个相关修复。作者无需把各 issue 的补丁 cherrypick 成一份人工联合补丁。若使用派生参考，明确记录 B、应用补丁及其 hash，不要称作自然 F。只有构建成功、无崩溃或单个数值变化，不能替代 B/F 几何差分。

按证据推进候选状态，可用 proposed、executable、calibrated、registered。没有可靠预期、baseline 未校验或 reference 尚未跑通的项保持 candidate/unknown，不进入 required checkpoint。允许保留大阶段 unknown/tentative；需要的是透明记录，不是人为补齐机制标签。

### 4. 为单个 issue version 准备题面与公开输入

每个 issue version 对应一个且仅一个 source baseline。单题的准入不依赖其他 issue 的 source、修复关系或测试覆盖。题面说明问题操作、几何对象和公开复现步骤，不暴露隐藏 evaluator 的 oracle、参考答案或负对照。公开输入放在 issue version 目录中，并在 issue.json 的 public_materials 中逐项列出。

所有 manifest 路径使用 bundle 内 POSIX 相对路径。不得使用绝对路径、路径穿越、指向 bundle 外部的符号链接或机器专属文件。公开输入变化、题面改变或 source baseline 改变时，创建新 issue version；不要覆盖旧材料。

### 5. 为单题选择必要检查

先为单个 issue version 选出能验证原始缺陷的可靠检查。每个 issue version 必须有 original 检查和至少两个独立 neighborhood test/checkpoint；当前五组的既有设计是每个 issue version 2 或 3 个 neighborhood checkpoint。按问题复杂度扩展时可增加测试，不要求固定恰好 3 个。neighborhood 的具体几何维度可按问题选择；不能以某个维度不适用为由取消多个邻域测试。regression 若确实不适用，写明证据边界和理由，不制造无关控制。

- original：用上游原始输入或可追溯的等价复现，确认 B 上的缺陷行为，并确认参考 F 能修复。
- neighborhood：围绕同一问题的适用几何条件或操作语境构造多个独立测试，检查修复是否只适用于原始输入。
- regression：相关的健康输入、无交/空结果或既有功能控制，用来确认修复没有制造错误结果；这些控制应在 B 和 F 上都满足原有几何语义。

一个 single suite 可以只服务一个 issue version。选择多 issue group 时，才需要一个 suite 覆盖其成员并声明兼容 group/source。当前框架中一条 checkpoint 清单行就是一个 test 入口，绑定一个 case 文件和 runner 调用。一个 case/test 可以内部执行多个 scenario：每个 scenario 通常是一份输入，或一个明确记录的输入组合/参数设置。scenario 内的曲线/曲面 sampling points 是测量采样点，不另算 scenario，也不能增加 test 数。每个 scenario 都要记录参数、预期关系和独立 Oracle verdict；任一 required scenario 失败或没有 verdict，该 test 就失败或不完整，不能只报最后一个总成功码。每条 checkpoint 要指定类别、visibility、trusted runner/oracle、bundle-relative case path、timeout、required 状态及必要的受限 runner_options。需要隐藏的 helper 和输入放在可信评测资产侧，并通过 suite 的 support_files 明确声明依赖。

### 6. 校准 Oracle，保留错误类别

Oracle 必须判断几何语义，而不是只判断命令是否结束。先推导几何期望，再实现判据；不得因某补丁未通过而调松阈值。对于解析几何，优先直接计算解析根、支持方程残差或集合/体积关系。对数值采样，记录模型单位、绝对/相对阈值来源、样本位置、非有限值处理和最差误差位置。

一次运行失败需要分清：

| 观察 | 应记录的结论 |
| --- | --- |
| 脚本和输入有效，geometry oracle 已执行且几何谓词不成立 | geometry_fail；可作为原始 B 失败证据 |
| B 上有效复现没有出现缺陷，oracle 已完成 | 缺陷未复现；不能算 geometry_fail，也不能用构建错误解释 |
| 配置、编译、链接失败 | build/configuration error；几何 oracle 未运行 |
| 输入缺失、格式错误、命令不存在或 Tcl/helper source 错误 | input/runner error；几何 oracle 未运行 |
| 超时、资源限制、SIGXCPU | timeout/resource-limited；单独报告 |
| Oracle 没运行、reference 不可用或期望仍未知 | not_run/unknown；不作为通过或几何失败 |

backend 的外层 failed/error 不能覆盖 oracle 内层 not_run。报告保留原始 stdout/stderr、结构化状态、checkpoint、输入和脚本 hash，以便复评。

### 7. 使用可信 evaluator 和冻结快照

Agent 只接触公开 statement、公开输入和任务要求。suite、隐藏 case、oracle helper、负对照及参考材料由 supervisor 持有。通过正式任务队列和 worker 运行，让 backend 按 group/suite/source identity 冻结输入和可信 evaluator。不要把 evaluator 私有路径写进 agent prompt，也不要把 Agent 提交的测试脚本当成可信 oracle。

freeze 必须使用已准备的 source cache，并核对 source_id、锁定 commit 和 materialized tree hash。冻结记录包含 suite、toolchain、catalog 和 snapshot hash；运行前后都要保留快照证据。只校验 catalog 或手动复制 evaluator 文件都不构成 freeze/replay 证据。

### 8. 维护版本并记录证据

将 issue、group、suite、source、toolchain、输入、oracle、patch 和运行日志的身份绑定到结果记录。每次改变公开材料或验收集时按[版本与稳定身份](#版本与稳定身份)提升相应版本/身份。正式注册前先运行只读 catalog validator；需要验证 DB 注册时使用专用临时 BENCH_DATA_DIR。注册本身不构建源码，也不运行几何检查。

最终报告应列出题目身份、source_id/commit/tree hash、suite 和 toolchain ID、每条 checkpoint 的 B/F/agent 状态、oracle 是否运行、原始日志位置、patch/input/oracle hash，以及未覆盖项。静态检查、注册、freeze、回放和正式 Agent 运行应逐项标记，不能用一个“通过”概括。

## 作者准入与 Agent patch 通过标准

下表是单 issue 作者准入时的核心几何校准要求。每个结论都要求该 issue 的准确 B/F 源码身份下，输入有效且 geometry oracle 实际运行。original 的 B fail/F pass 是单题准入核心；多个独立 neighborhood test/checkpoint 是单题准入必需覆盖，参照现有每个 issue version 的 2–3 条设计。regression 视问题与风险确定；确实不适用时说明依据和覆盖边界，不把它伪报成通过。

| Checkpoint 类别 | B 基线要求 | F 参考要求 | 作者准入判断 |
| --- | --- | --- | --- |
| original | 至少一个代表原始缺陷的 required case 为 geometry_fail | 对应 case 为 geometry_pass | 可证明缺陷确实可触发且参考可修复 |
| neighborhood（至少多个独立 test/checkpoint） | 每个 test 的场景结果逐项记录；B 可通过也可失败，按观察保留 | 每个 required scenario 都须在可信 F 上 geometry_pass | 一个 test 中的多场景不计成多个 test；任一 required 场景失败/无判据，该 test 不通过 |
| regression（适用时） | 回归/健康控制应维持预期几何行为 | 与 B 一样 geometry_pass | 任一 baseline 上出现几何失败，先检查回归、输入或 oracle；不适用时说明边界 |

上表要求的原始缺陷、邻域和回归几何判据不能靠 build rc=0、进程正常退出、TEST_DONE marker、IsDone 或“没有崩溃”替代。分支数、体积、checkshape、tolerance 等可在直接对应缺陷语义且期望值可复核时作为有效 Oracle；不要求所有题都增加全面曲面残差。对有必要的每个 issue version 记录原始 B/F 证据；若该问题用的是派生 baseline，应明确派生过程和身份。

未来 Agent patch 的正式通过则是另一道门槛；它只要求通过这个 single task 自身所声明的 required suite，不要求和其他 issue 联合提交。每个 neighborhood test 的所有 required scenario 都要分别通过，不能用一个 test 中通过的场景抵消另一个场景失败：

1. 提交该 group manifest 要求的产物；当前新组要求 patch.diff 和 report.md。缺少必需产物时任务不完整。
2. 评测使用与任务一致的锁定 B source、group/suite 版本、toolchain、冻结 snapshot 和 supervisor evaluator。
3. patch 应用于正确基线并完成配置与构建；构建失败属于技术/基础设施结果，不是几何通过。
4. 所有 required original、neighborhood 和 regression checkpoints 都实际执行并由可信 Oracle 判为 geometry_pass；每个 issue version 的多个 neighborhood tests 都要通过，且每个 test 内的 required scenario 都要逐个通过。required case/scenario 的 timeout、error、not_run、skipped 或几何失败都不能算通过。
5. report.md 解释改动、证据和限制，但不能覆盖 evaluator 结果；新增测试不能由 Agent 自己定义后作为验收 oracle。

backend 的 technical_passed 表示当前冻结 suite 中所有 required checkpoints 的执行状态为 passed。它是 Agent 技术验收的一部分；作者对 suite 的 B/F 校准、source 证据、类别覆盖及实际几何判据仍需单独留档。空类别显示“未配置”，不代表该类已通过。

## 多维邻域设计

邻域要覆盖会影响同一已证实缺陷大阶段或几何语义的代表变化，不能做没有假设的笛卡尔积，也不要求每个 issue 都适用所有维度。每个 issue version 至少有多个独立 neighborhood test/checkpoint，参考当前每题2–3条；在此基础上按问题机制、复杂度和可判定输入决定是否增加测试。同一 test 可包含多个 scenario，但必须逐场景给出判据和结果，不能用一个总返回码掩盖失败。曲线误差测量中的采样点不按独立 scenario 计数。

当前五组的邻域扩充曾按 canonical issue number 设置过最多 15 个场景的局部预算；这是场景预算，不是 test 数，也不是任何 issue 必须凑满的数量。新题按当前正式设计至少提供多个（参照每个 issue version 2–3 条）独立 neighborhood test；复杂输入可让一个 test 覆盖多个场景，但不能把场景数充作 test 数。若继续扩充同一五组中的 issue，请沿用该组明确的场景预算规则并统计同一 issue number 的不同版本。

| 维度 | 常见变化 | 需要保持或重推的关系 |
| --- | --- | --- |
| 刚体等价变换 | 对所有输入施加相同平移、旋转或组合变换 | 拓扑/分支语义不变；必要时逆变换输出再比对 |
| 尺度 | 选择不同数量级且仍在算法支持范围内 | 长度按 s、面积按 s²、体积按 s³；残差阈值按模型单位重推 |
| 几何参数 | 半径、轴距、夹角、裁剪范围、球心等 | 每种参数有解析解、可信参考或独立配对关系 |
| 参数化与周期缝 | 改周期起点、等价 U 区间、交换方向、跨缝 | 比较物理曲线/端点图和域包含，不盲比参数数值或曲线排序 |
| 机制边界 | 近相切、短曲线、相近轴线、退化端点 | 推导边界两侧预期和数值余量，不把真正相切与近相切混用 |
| 拓扑/否定控制 | 无交、单支、多支、空 Common、非空 Cut、有限面裁剪 | 同时检验存在性、连通分量、根分配和有效域 |
| 操作顺序/表示 | 交换两面、分步/同时 Boolean、等价表示 | 先确认语义等价，再比较集合、体积或几何残差 |

先用单维变化定位，再为高风险交互选少量组合，例如尺度与周期缝、平移与端点切向。扩充前检查主要失效分支是否有见证、是否有只适用于原坐标/尺度/方向的补丁仍能通过、判据是否足以拒绝错误结果，以及新点是否提供不同信息。若项目明确设定了上限而仍有覆盖缺口，替换冗余点、收窄声明或记录未覆盖项，不得继续堆案例，也不能把“达到 N 个”当充分性证明。

覆盖表分开报告 checkpoint 数、参数样本数和适用维度数。一个 case 含多个样本时逐项保存参数、观测和 oracle verdict；固定代表点要给出理由，随机采样要保留种子、生成器版本和完整参数列表。

## Oracle 校准与负对照

每条 Oracle 说明测什么、怎么测、阈值从哪里来、和待修库共享什么实现，以及什么结果能明确拒绝错误补丁。

### 按问题语义选择几何判据

- 执行层：构建、runner 启动、输入加载、oracle 确实执行。这些条件必要，但构建成功、进程退出码、TEST_DONE marker 或 IsDone 单独不能证明几何正确。
- 几何层：按 issue 的缺陷语义选择直接相关且可复核的判据。缺陷是 Boolean 体积错误时，正确推导的体积可作核心 oracle；缺陷是缺失/多余交线时，分支数或根覆盖可作核心 oracle；缺陷是形状拓扑无效时，checkshape 可直接验证该属性；缺陷涉及 p-curve 到 3D 的一致性时，才需要相应映射残差。结构、拓扑、体积和 branch count 都可以是几何 oracle 的一部分，不需要每题都升级成完整曲面残差或全面采样。
- 数值层：对本题实际使用的量记录尺度/单位、绝对与相对阈值、有限数和适用采样位置。只有当问题语义依赖连续曲线/曲面误差时，才要求端点、内部或周期缝附近采样。

Tolerance Reached、SetTolerance、dot、IsDone、checkshape、分支数和体积都不能脱离问题语义单独判定。它们若直接对应缺陷，可作为有效几何判据；若只是命令成功或指标上报，则不足以证明正确。必须拒绝 NaN/Inf、未定义变量、空采样和 Oracle 未完成。固定有限采样不是连续域证明；只有在采样是必要判据时，才需说明它的覆盖边界、异常处加密并保留最差位置。

独立性要准确表述。“另一个进程执行”不等于“另一个数学判据”。用被修库的 xdistcs 等功能测量，比读取同一库上报的 tolerance 更有价值，但仍共享实现；有解析支持方程时再加直接残差。无法独立验证时，写明剩余依赖，不声称 Oracle 完全独立。

当问题涉及精度或 tolerance 时，将实际几何误差上限、上报 tolerance 的语义、历史参考值一致性分开。缩放后按量纲重推相关阈值；不能因为补丁失败而调松阈值，也不能把更小的上报 tolerance 自动视为更准确。非精度类问题不需要机械附加完整残差测试。

### 正负对照与代表例子

- 锁定 B 用于定位缺陷；不是每个邻域都要求 B 失败，健康邻域应如实标记。
- 可信 F 用于校准可满足性和期望值；记录 commit/patch/tree hash。单 issue F 不自动等于组合组完整参考。
- 既有 Agent patch 用于检查泛化缺口，不能反过来当 oracle expected 值的唯一来源。
- 按本题风险选择错误补丁负对照，例如硬编码 tolerance、错误分支/域扩展、丢 p-curve 或只修 dot；不要求每题机械覆盖所有机制。记录被哪条 assertion 拒绝。若未拒绝，明确写“负对照未被拒绝”。
- 无交/健康控制防止总返回非空、硬补曲线或留下旧结果。

已有例子保留其边界：M27780 的端点方向 dot 为正只验证一个子条件，还要测 p-curve 经曲面映射与 3D 曲线的一致性；M30082 的上报 tolerance 不是实际曲面残差证据。2026-10 的 DSH M30082 patch 使用 aTolC = 6.5e-7 并通过旧 suite；若采用，应将该类补丁作为负对照，检查真实残差和上报值的一致性及尺度/参数变化。若新用例未能拒绝它，要直接记录结果，不能用案例数量掩盖。

## 清单格式与目录结构

完整目录结构可参考 [benchmark-example](benchmark-example/)。当前共享 OCCT bundle 目录和稳定身份见 [benchmarks/occt/README](../benchmarks/occt/README.md) 及 [NAMING_MAP](../benchmarks/occt/NAMING_MAP.md)。

    my-benchmark/
      catalog.json
      sources.lock.json
      issues/<issue-id>/<version>/{issue.json,statement.md,public/*}
      groups/<group-id>/<version>.json
      evaluation/suites/<suite-id>/<version>.json
      evaluation/cases/                 # supervisor-only trusted cases
      evaluation/provenance/            # provenance and evidence
      tools/<tools-directory>/          # reviewed build/run helpers
      toolchains/<toolchain-id>.json

catalog.json 只列 versioned issue、group、evaluation suite 的稳定 ID、版本和清单路径。目录名与稳定 ID 可以不同；程序按 catalog identity 映射，不能从目录名推断身份。所有引用都必须在 bundle 内且不经过符号链接。

### Issue 清单

issue.json 至少含 schema_version、id、version、title、source_id、相对 statement 路径和非空 public_materials。issue id/version 必须与 catalog 完全一致；每个 issue version 只能绑定一个 source_id。issue statement 和公开材料必须在该 issue version 路径内。

### Group 清单

group manifest 至少声明 schema_version、id、version、title、kind、source_id、execution_mode、成员 issue/version、group wall_seconds 预算、required_outputs 和 evaluation_suite 引用。kind 是 single、group 或 active；execution_mode 是 joint 或 independent。kind=single 必须恰好有一个成员，这是当前 validator 支持单 issue task 的正式路径。可选的多 issue group 不要求三名成员或固定规模；但当前 validator 要求每个成员的 source_id 都等于 group.source_id，因此一个 multi-member group 不能在 manifest 中混合不同 B baseline。joint 也不能混用 baseline。改测不同 baseline 的单题时，创建各自的 single task 并分别导入/评测，不要把它们强行塞进同一 group。group 更新不得复用同一个 ID。

required_outputs 当前允许 patch.diff、report.md、findings.jsonl；active 题必须要求 findings.jsonl。最终 Agent 任务的产物要求以对应 group manifest 为准。

### Suite 清单与 evaluator contract

suite 声明兼容的 source_ids、group_ids 和非空 checkpoints。每条 checkpoint 需要唯一 id、category（original/neighborhood/regression）、visibility（public/hidden）、trusted runner/oracle、case 路径、timeout_seconds 和 required；可选 issue_id 和受限 runner_options。

当前注册 runner 为 draw_case_v1 与 cpp_case_v1。DRAW 的 checkpoint.case 是唯一 Tcl script 路径并作为 --script 传给 runner；runner_options.script 会被拒绝。suite manifest 不能提供 shell 命令。C++ runner 只接受受信任的 OCCT library 名、bundle-relative inputs 和 stdout marker。runner 只在声明的 timeout/resource 限制下运行。case 或 helper 缺失必须报错，不得静默回退到 reproduce.tcl。

隐藏 case 和 support_files 必须安全地位于 bundle 中。冻结时将可信 evaluator 资产复制到 supervisor 侧。可见性字段或文件放在 evaluator/cases 目录里并不自动证明它已正确隐藏；应按 freeze snapshot 核查 agent workspace 与 supervisor bundle 的边界。

多 issue 是附加编排，不是单题准入前提。若选择联合评测，应说明成员的大阶段为何兼容、是否有已证实的相互作用，并在共同 B baseline 上分别复现每个成员的 original；可信 F/reference 应能验证组合 suite 中声明的修复行为。这里没有成员 issue 相似度分数、group overlap ratio、必须三题或历史 Part2 半数约束。若没有可验证的共同 F 或联合测试理由，优先拆成独立 single tasks；不要求人工 cherrypick 各 issue 补丁制造联合参考。

### Source lock 与 toolchain

每个 source lock entry 唯一指定 source_id、upstream_url、完整 40 位 commit、materialized_tree_sha256、verification_status、provenance 和 toolchain profile。树哈希按排序后的 POSIX 相对路径、文件类型、可执行位、字节数和内容计算；排除 .git、__pycache__、CMakeFiles、任意 build 路径组件以及 .pyc/.pyo。符号链接内容按链接文本哈希且不得逃出根目录。

自然上游 commit 必须来自本地可验证 Git 对象并与锁定树 hash 一致。source_cache 从本地仓库导出，不会 clone、fetch 或访问网络。没有 Git 元数据的 export 只能显式标成 unverified，并匹配已记录 tree hash；它不能证明自然 commit。正式历史 B/F 结论若无法验证来源，保留为 candidate/unknown。

toolchain profile 固定编译器、CMake、Tcl、工具目录、runner 目录和 compiler_jobs_max。validator 要求 compiler_jobs_max 在 1 到 2 之间。source cache 有每 source 锁和原子发布，发布后的源文件只读；worker 会为任务复制可写工作树。路径由项目设置或环境变量提供；公共清单和说明不要写用户 home、机器缓存目录、个人 Conda 环境名或代理信息。

## 版本与稳定身份

已有 group、suite、issue、source ID 是历史 run 和任务选择的兼容接口。改动规则如下：

| 变化 | 版本/身份规则 |
| --- | --- |
| 新增 issue | 新建 issue ID/version 目录与 issue.json，并在 catalog 增加引用 |
| 修改 issue statement、公开输入或该 issue baseline | 新建 issue version；baseline 变化时同时新增 source lock/provenance/toolchain 对应记录 |
| 新增题组，或改变成员、budget、execution_mode、outputs | 新建 group ID 和 manifest；旧组保留 |
| 只增删改 checkpoint/oracle/case | 新建 suite version，catalog 更新 suite 引用；历史 snapshot/result 不改写 |
| 新 suite 要成为新任务的默认套件 | 新建 group ID 指向该 suite；不要覆盖旧 group |
| 改 toolchain/runtime、case helper 或公开评测材料 | 重新校验 source/task hash 与实际 freeze 资产；若输入语义改变，提升对应 issue/suite/group 身份 |

当前 validator 不允许相同 group ID 出现多个版本；不要仅提高 group.version 后覆盖旧条目。数据库只允许完全相同的 id/version payload 幂等注册；同 id/version 内容不同会冲突。不要清数据库、关闭冲突保护或改版本来掩盖未查明的 payload 差异。

## 常用命令与运行顺序

以下命令使用变量占位符，在项目配置的 Conda 环境里运行。先在专用环境设置 FRAMEWORK_ROOT、BENCHMARK_ROOT 和 BENCH_CONDA_ENV；需要写数据库时再设置专用 BENCH_DATA_DIR。不要让注册命令落到共享或正式数据库。

### 只读清单校验

backend.catalog 只读验证 catalog/schema 引用、source lock 结构、suite/group 兼容性、case/support file 路径、runner/oracle 类型和工具链字段；它不会访问源码缓存、构建 OCCT 或运行几何 case。

    set -eu
    cd "$FRAMEWORK_ROOT"
    conda run -n "$BENCH_CONDA_ENV" python -m backend.catalog --root "$BENCHMARK_ROOT" --json

### 专用临时数据库注册

只有需要确认 catalog 导入路径时才执行。该操作写数据库，但不会准备源码缓存、freeze evaluator、构建或运行几何检查。

    set -eu
    AUTHORING_TMP="$(mktemp -d)"
    export BENCHMARK_ROOT
    export BENCH_DATA_DIR="$AUTHORING_TMP/data"
    unset BENCH_PROTO_ROOT
    cd "$FRAMEWORK_ROOT"
    conda run -n "$BENCH_CONDA_ENV" python -m backend.import_proto

导入前确认 BENCH_DATA_DIR 指向本次临时目录。catalog 校验成功不要求执行导入；不要为静态文件检查写入正式数据库。

### 本地准备锁定 source cache

source cache 准备只从本机已有 Git 对象库导出锁定 commit，不联网。必须传入 catalog 中的 source_id，以及该 commit 所在本地 Git checkout。

    set -eu
    export BENCHMARK_ROOT
    export BENCH_CACHE_DIR
    cd "$FRAMEWORK_ROOT"
    conda run -n "$BENCH_CONDA_ENV" python -m backend.source_cache "$SOURCE_ID" --from-dir "$LOCAL_GIT_REPO"

若本地没有锁定 commit、commit/tree hash 与 lock 不匹配或缓存已有损坏条目，停止并保留错误证据；不要从网络拉取“近似版本”或覆盖 cache。

### 保存 patch 的离线重评

有 patch 文件、锁定 source cache 和 suite 时，可用 backend.reevaluate 对明确 source/suite 做离线评测。它不调用 Agent/model，但会执行真实 patch apply/build/evaluator；使用独立 BENCH_DATA_DIR、BENCH_WORK_DIR 和适当 cache 配置。该命令是实际几何运行，不属于只读文档/静态清单验证。

    set -eu
    export BENCHMARK_ROOT
    export BENCH_DATA_DIR
    export BENCH_CACHE_DIR
    export BENCH_WORK_DIR
    cd "$FRAMEWORK_ROOT"
    conda run -n "$BENCH_CONDA_ENV" python -m backend.reevaluate \
      --patch "$PATCH_FILE" \
      --source-id "$SOURCE_ID" \
      --suite-id "$SUITE_ID" \
      --suite-version "$SUITE_VERSION"

reevaluate 对 patch 文件要求显式 source-id，并将结果作为独立 evaluation 记录；不覆盖旧 run 或分数。正式 Agent acceptance 应从 worker 的冻结任务流程执行，使用 Agent 实际提交的 patch.diff 和 report.md。详细任务入口和部署配置见 [项目 README](../README.md)。

## 当前五组磁盘快照

下表是在 2026-10-26 按当前 catalog、group、suite 清单重新统计的清单数。五个既有新组包含 12 个不同 issue ID、15 个 issue versions 和 73 条 required test/checkpoint；分别是 19 original、39 neighborhood、15 regression。现有 73 条校准/回放清单已按各自预定标准通过（包括 original 的 B fail/F pass 等角色结果，并非所有输入都应返回同一种通过极性）；本次文档整理只重数当前清单并做 catalog 校验，没有重跑这 73 条。该通过状态来自现有题库记录和本任务用户确认，不是由本次静态检查推得，也不是未来题目的成员数配额。

| Group ID | Suite ID | 每成员 neighborhood tests | Original | Neighborhood tests | Regression | Required 总数 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| NG-04R-v2 | NG-04R-checks-v2 | 各2 | 3 | 6 | 3 | 12 |
| NG-05T-v1 | NG-05T-v1-checks | 各2 | 3 | 6 | 3 | 12 |
| occt-bf-group-d9d310-21494-29807-31835 | occt-bf-suite-d9d310-21494-29807-31835 | 各3 | 6 | 9 | 3 | 18 |
| occt-bf-group-b55-27310-27773-27252-oracle-v2 | occt-bf-suite-b55-27310-27773-27252-oracle-v2 | 各3 | 4 | 9 | 3 | 16 |
| occt-bf-group-b2613378-27780-27252-21494-v1 | occt-bf-suite-b2613378-27780-27252-21494-v1 | 各3 | 3 | 9 | 3 | 15 |
| **合计** |  |  | **19** | **39** | **15** | **73** |

按 issue version 的 neighborhood test/checkpoint 数核对如下；表中每条清单行是一条测试，不是 scenario 数：

- NG-04R-v2：mantis-30082@2、mantis-30202@2、mantis-33541@2，各 2 条。
- NG-05T-v1：mantis-30082@4、mantis-31602@2、mantis-32850@1，各 2 条。
- d9d310 组：occt-21494@1、occt-29807@1、occt-31835@1，各 3 条。
- b55 组：occt-27310@1、occt-27773@1、occt-27252@1，各 3 条。
- b2613378 组：occt-21494@2、occt-27252@2、occt-27780@1，各 3 条。

全 catalog 当前通过只读 validator 后报告 24 issue versions、12 groups、12 suites 和 6 source identities。现有五组每组有三个成员只是历史布局事实，不是单题配额。较新的 [neighborhood-v2-coverage record](../benchmarks/occt/evaluation/provenance/neighborhood-v2-coverage.json) 记录 73 条静态 dispatch routes、24 条新增 frozen geometry pass 和此前 49 条保持不变；该轮没有重放旧 49 条。本轮没有重跑。较早的 [NAMING_MAP](../benchmarks/occt/NAMING_MAP.md) 与 [integration-validation record](../benchmarks/occt/evaluation/provenance/integration-validation.json) 中的 49 项/19-15-15 是更早快照；不要将它们视为当前清单计数。

## 现有示例与证据链接

- [可复制的最小题库](benchmark-example/) 展示 issue、single/group、suite、sources.lock、toolchain 和 provenance 文件组织。
- [共享 OCCT bundle README](../benchmarks/occt/README.md) 和 [stable identity/naming map](../benchmarks/occt/NAMING_MAP.md) 保留 group、issue、suite 路径映射。NAMING_MAP 中 checkpoint 数是较早快照，更新时请直接从当前 catalog/suite 清单重算。
- [neighborhood-v2-coverage record](../benchmarks/occt/evaluation/provenance/neighborhood-v2-coverage.json) 包含现行 73 路由统计、24 个新增 frozen checkpoint 的几何通过结果及旧 checkpoint 是否重放的边界；它不能单独证明旧 49 项在该轮又重跑一次。
- [integration validation record](../benchmarks/occt/evaluation/provenance/integration-validation.json) 保留较早的 catalog、freeze、dispatcher 和验证边界；它是历史证据，不追溯证明本次或之后修改的 suite。
- NG-04R-v2 和 NG-05T-v1 的参考补丁分别保存在 [NG-04R reference patch](../benchmarks/occt/evaluation/provenance/NG-04R-v2-reference.patch) 与 [NG-05T reference patch](../benchmarks/occt/evaluation/provenance/NG-05T-v1-reference.patch)。三个 BF 组的自然 F commit、原 B/F 身份和历史几何证据入口，见 [g1 original-bundle notes](../benchmarks/occt/evaluation/provenance/source-packs/occt-five-groups/docs/original-bundles/g1/README_ZH.md)、[g2 notes](../benchmarks/occt/evaluation/provenance/source-packs/occt-five-groups/docs/original-bundles/g2/README_ZH.md)、[g3 notes](../benchmarks/occt/evaluation/provenance/source-packs/occt-five-groups/docs/original-bundles/g3/README_ZH.md) 和 [external evidence archive manifest](../benchmarks/occt/evaluation/provenance/external-evidence-archive.json)。原始 sidecar/日志的 archive hash 仍按这些记录追溯；本指导合并不改动或替代历史实验材料。
