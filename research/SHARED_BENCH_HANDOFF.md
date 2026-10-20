# 共享实验工具：Luna 执行与验收方案

日期：2026-10-14。本文规定待实施工作，不代表功能已完成。

## 1. 范围、部署与执行约束

目标：同学将仓库 clone 到自己的用户目录，使用各自系统账号、环境、凭据和运行数据；通过 Git 同步代码与题库，不依赖项目所有者的 checkout 或个人环境。

本轮交付：

- 题目及必要输入入仓，源码按锁定 commit 准备到仓库外缓存，支持不同题目使用不同基线。
- 清除机器相关硬编码；依赖明确、数据外置、可独立部署。
- 明确 issue、题组和评测套件格式，通过清单接入新题；支持多检查点、分类汇报和隐藏检查。
- 原样迁移已有检查；支持旧补丁运行显式选择的新版检查点。
- 接入 Codex，与 DSH 共用执行流程，增加有限恢复。
- Linux 执行；Mac 等平台读取/校验题库，通过浏览器和 SSH 隧道使用 Linux 服务。

本轮不做：升级正式检查内容、Mac/Windows 本地执行环境、跨账号共享缓存或全局调度系统、多租户账号系统、自动缓存清理、补丁跨 commit 移植、Plan 1B 研究协议改造。

执行约束：

- 无 root 权限，不 sudo、不全局安装；新增依赖或 CLI 安装先说明具体内容并取得确认。
- 框架 Python 测试在已配置的 conda 环境运行。共享项目不固定环境名称，工具链只从实际配置的环境派生运行时变量。
- 开发使用独立 data/work、端口和 worker ID；保护既有 git 修改、活动服务、原题库和旧实验，不主动切换生产服务或 push。
- 先完成离线验收；付费模型 smoke 需另行授权模型和预算。源码准备优先核验本地资源，不自动大规模下载。
- 代理从环境或配置读取，不写死本机端口；本轮不需要 GPU。
- 按已确定范围持续实施；遇到安装、付费或实际部署条件缺失时，完成其余工作并报告具体待验证项。

## 2. 配置、依赖与数据迁移

### 2.1 目录和依赖

```text
benchmarks/occt/
  catalog.json
  sources.lock.json
  issues/<id>/<version>/issue.json
  issues/<id>/<version>/statement.md
  issues/<id>/<version>/public/       # 复现与必要输入
  groups/<id>/<version>.json
  tools/
  evaluation/suites/<id>/<version>.json
  evaluation/cases/                   # supervisor 材料
  evaluation/provenance/              # 来源与修复指针
schemas/
docs/
config.example.json
requirements.txt
requirements-dev.txt
environment.yml
```

目录名可适当调整；清单统一使用 JSON。

- `requirements.txt`：框架运行所需直接 Python 依赖及经过验证的版本约束，不能用个人环境的整份 pip freeze 代替。
- `requirements-dev.txt`：引用运行依赖，补充实际需要的测试/开发依赖；使用 unittest 不必另加测试框架。
- `environment.yml`：Python 版本和 conda 创建方式，复用 requirements，不重复维护冲突的 Python 包版本。
- 系统/执行依赖另列：Git、Node、编译器、Tcl、bubblewrap、agent CLI 的用途、平台和版本要求。DSH 保留 package.json/锁文件，Codex 记录固定 CLI 版本。
- 说明题库读取、网页运行、框架测试、Linux 实验执行各自需要哪些依赖，题库读取不强制安装编译/沙箱工具。

### 2.2 配置和数据

统一配置题库、data/cache/work、工具链、CLI、并发、端口、代理与认证来源。优先级：CLI > 环境变量 > 配置文件 > 默认值；凭据不进入日志或冻结快照。

- 默认题库为仓库内目录，保留外部题库配置；旧 `BENCH_PROTO_ROOT` 可作为明确优先级的兼容别名。
- data/cache/work 默认位于各自仓库外的用户目录，均可覆盖；不依赖启动 cwd。默认每账号内部源码去重，资源使用通过实例并发参数和同学间配额约定控制。
- 清除个人 home、conda 安装目录、环境名、固定服务地址、编译器/Tcl 路径等机器假设。沙箱内 `/workspace`、`/evaluation` 属于协议路径，可保留。
- 旧 data 提供显式迁移脚本及备份/校验/回退说明，不静默切换到空数据库；允许用配置继续读取旧位置。数据库使用 SQLite backup API，保留原数据和历史路径，不要求建设复杂路径重写系统。
- 提供只读 `doctor` 检查依赖、源码和隔离能力，不自动安装。

## 3. 题库与评测数据契约

### 3.1 源码与 issue

`sources.lock.json` 定义不可变 `source_id`，包含上游地址、完整 commit、物化树哈希、可选基线补丁及工具链配置引用。源码缓存位于仓库外，每个基线准备一次；下载/导入加锁，核验完成后原子发布。

树哈希算法需明确排序、文件内容/类型/执行位及符号链接规则，排除 Git 元数据和构建缓存。现有源码没有 `.git`，先验证其与清单 commit 是否一致；无法验证时标记未验证，不能冒充上游原样基线。有差异时保存可追溯基线补丁或仓库外归档。

**每个 issue 版本固定一个 source_id。** 更换 commit 或公开材料时新增 issue 版本，不维护同一版本的多基线材料映射。issue 清单包含 `schema_version/id/version/title/source_id/statement/public_materials`。

agent 使用独立源码副本；缓存不可写，不使用普通硬链接共享可写文件。构建缓存若复用，键还需包含工具链、架构和构建参数。

### 3.2 题组

```json
{
  "schema_version": 1,
  "id": "occt-group-a",
  "version": "2",
  "title": "圆角问题组",
  "kind": "group",
  "source_id": "occt-base-a",
  "execution_mode": "joint",
  "members": [
    {"issue_id": "occt-690", "issue_version": "1"},
    {"issue_id": "occt-693", "issue_version": "1"}
  ],
  "budget": {"scope": "group", "wall_seconds": 1800},
  "required_outputs": ["patch.diff", "report.md"],
  "evaluation_suite": {"id": "occt-group-a-eval", "version": "1"}
}
```

单题使用相同结构；joint 题组成员必须属于同一基线。不同基线可以同处题库/实验批次，分别执行。保留旧 active 题型读取和实际能力状态，不把发现格式检查当成发现质量评分。

校验引用、版本、成员唯一性、基线兼容、预算、输出与相对路径安全。同 ID/version 内容不同拒绝覆盖，相同内容导入幂等。新题或题组通过清单接入，不新增题目 ID 分支。示例预算不覆盖旧清单或既有冻结实验预算。

### 3.3 检查点与结果

评测 suite 独立版本化，声明兼容的 source_id 和适用 issue；检查点格式：

```json
{
  "id": "issue-690-original",
  "issue_id": "occt-690",
  "category": "original",
  "visibility": "public",
  "runner": "draw_case",
  "case": "issues/occt-690/1/public/reproduce.tcl",
  "oracle": "legacy_draw_done_v1",
  "timeout_seconds": 30,
  "required": true
}
```

- `category` 为 original/neighborhood/regression；`visibility` 为 public/hidden，两者独立。组级检查的 issue_id 可为 null。
- runner/oracle 为可信注册项，可复用 DRAW/C++ 等执行技术；不接受前端任意 shell 命令。检查 ID 唯一，路径不越界。
- 本轮保留原检查输入、断言、超时和适用任务集合；仅用测试 fixture 验证新增类别及隐藏能力，不扩充正式 OCCT 检查。
- 结果保存检查 ID、issue、类别、可见性、状态、耗时和证据引用。状态区分 passed/failed/timeout/error/not_run/skipped，跳过须有理由；编译失败单列阶段，未执行项为 not_run。
- 每类展示声明数、执行数和各状态数，空类为“未配置”；所有 required 检查通过才算技术通过，报告完整性另列。既有 Plan 1A 完整成功/资产准入保持原语义。
- 题面/基线变化更新 issue 或题组版本；只增改检查时更新 suite 版本，不强制复制 issue。运行入队时冻结所有引用、材料/工具/判据哈希、工具链、agent 配置、提示词及预算。
- 旧结果保持原评分；缺少类别的旧检查显示 legacy，不猜测重算。对比默认使用同版本，跨 suite 对比明确检查集合差异。

## 4. 执行、隐藏隔离与旧补丁复评

### 4.1 共用执行与隔离

生命周期统一为：领取任务 → 冻结输入 → 准备工作区 → 运行 agent → 收集源码补丁 → 独立评测 → 保存结果。DSH/Codex 适配器负责各自 CLI、事件、取消和会话协议。

- agent 工作区按白名单组装，只包含基线源码、公开题面/复现和必要工具；不挂载完整项目、隐藏材料、源码 Git 历史、真实 home、凭据或其他运行目录。
- 共享仓库中的隐藏测试对同学可读，对 agent 不可读；公开 API/导出不泄漏隐藏输入、断言、路径和日志，不把隐藏反馈发送给模型。
- 评测在原基线干净副本上应用补丁，使用可信测试和工具；agent 修改测试不能改变正式判定。若初始化 Git，仅用独立基线树，不连接上游历史缓存。
- 修复 PR/commit 来源保留于 supervisor provenance，不进入 agent 题面；整理题面形成新版本，不改旧冻结材料。
- Linux 保留 bubblewrap 边界；缺少能力明确不可执行，不降级裸跑。题库读取模块不导入 Linux 专用模块。
- Plan 1B 保留既有读取/执行兼容；本轮不要求其接入 Codex。

### 4.2 旧补丁运行新版检查点

必须提供离线 CLI，接受旧 run ID，或补丁文件 + source_id；显式选择目标 suite ID/version。无需 agent 会话、模型调用或重新生成补丁。

1. 核验原始源码基线与目标 suite 兼容，在干净副本检查并应用原补丁；不自动 rebase、改补丁或解决冲突。不能核验基线时明确标记，不能静默使用当前默认基线。
2. 执行目标 suite，创建独立 evaluation，保存来源、补丁哈希、基线哈希、目标 suite/工具链及逐项结果。队列提交后 suite 保持冻结。
3. 缺少旧报告仍可执行新检查，报告状态单列；仅复现旧协议时遵循其原报告门槛。
4. 不覆盖旧评分、补丁或运行快照，不自动改变 K1/M0 等资产资格。旧补丁与新版检查产生不同结果是允许的。

本轮以 suite v1/v2 fixture 验证新检查确实执行，以已有 OCCT 补丁验证真实导入和评测通路；正式检查升级留待后续。

### 4.3 Codex 与有限恢复

固定并记录实际 CLI/模型 ID、结构化事件、明确 session ID、usage 和退出状态；恢复指定 session，不用 `--last`。每运行隔离配置/会话，不继承个人插件、hooks、历史记忆或额外 MCP。

认证留在可信端，agent shell/构建程序不能读取。现有 DeepSeek 专用网关不能原样用于 Codex；根据固定 CLI 能力实现并验证认证隔离，未通过则 live disabled。API 可用性按适配器和运行环境判断，不能沿用全局验证标记为所有适配器背书。

| 情况 | 默认处理 |
| --- | --- |
| 明确可重试的限流/服务端临时失败 | 退避恢复，外层追加最多 2 次 |
| 断连、结果未知 | 先核对会话和工作区，避免重复执行 |
| 工具审核拒绝导致会话提前终止 | 最多 1 次续接，继续允许的工作；未终止不额外续接 |
| 相同拒绝再次出现、明确模型安全拒绝、认证失败、取消、预算耗尽或未知错误 | 停止自动恢复，保留证据 |

外层恢复总数最多 2 次，工具拒绝续接占其中最多 1 次；先结束原进程，不并行恢复。保持原权限、模型和身份，不重复提交被拒绝命令或提示规避审核。CLI 内部重试与外层恢复共用累计预算，worker 重启不自动付费续接。

记录首次完成状态、恢复动作和最终状态，预算不清零。只能记录实际可观测的请求/turn/token/耗时，不能把 turn 冒充请求次数；能力不足时明确限制。

CLI 参数与事件按本地版本及官方文档核对：https://learn.chatgpt.com/docs/non-interactive-mode 。

## 5. 实施顺序与交付物

执行前重新核验：外部 7 个任务的映射与源码、固定题组 dispatch、机器路径、已有评测集合、Plan 1A/1B 和资产关联。重点文件包括 proto_config/import_proto/worker/evaluator/eval_driver/adapters/app/study、相关 worker 和前端；不要只改注册表。

| 阶段 | 工作及交付 | 验收组 |
| --- | --- | --- |
| P0 清点 | 原有离线测试基线、题目/源码/检查映射和既有失败；确定 schema | V03、V06 |
| P1 部署 | 配置、requirements、doctor、数据迁移与回退 | V01、V02、V13 |
| P2 题库 | 材料入仓、源码准备/缓存、清单校验与通用执行 | V03–V05 |
| P3 评测 | 原检查迁移、多检查点、分类 UI/导出、旧补丁复评 | V06–V09 |
| P4 Agent | 共用生命周期、DSH 兼容、Codex、恢复与认证隔离 | V10–V12 |
| P5 交接 | 独立 clone 验收、使用说明、报告和已知限制 | V01、V13、V14 |

文档交付：README 快速开始；部署/依赖/SSH；加题与多 commit/题组/检查点例子；agent 配置与恢复；旧补丁新套件复评；数据迁移和回退。所有示例不绑定个人路径、用户名、IP 或端口。

## 6. 验收与完成标准

框架 Python 测试在 conda 环境运行；OCCT 评分在 Linux 评测沙箱/工具链运行；前端用声明的 Node/浏览器工具验证。已有测试按变化范围运行；不为扩大覆盖反复全量构建，真实 OCCT 验证编译并发最多 2，先检查服务器负载。

| ID | 验收组 | 必须验证 |
| --- | --- | --- |
| V01 | 独立部署与读取 | 独立 clone、无原型目录可列题；不同 cwd 行为一致；两个实例 data/work/会话不混用；Mac 可读清单，读取路径无 Linux 执行依赖 |
| V02 | 依赖与硬编码 | requirements 分层及系统/CLI 依赖明确；新环境按文档可启动/测试；共享文件无个人路径及固定服务地址 |
| V03 | 题库契约 | 7 个旧任务有映射和能力状态；新题组只增材料/清单即可接入；重复成员、坏引用/预算、路径逃逸和混合基线 joint 组被拒绝 |
| V04 | 多基线与缓存 | 两个本地 commit fixture 选择正确；同基线只准备一次；并发/失败不发布半成品；运行修改不影响缓存或其他运行；实际 OCCT 基线核验有证据 |
| V05 | 版本冻结 | 同版本不同内容拒绝；排队后修改材料不影响运行；suite 可独立更新，旧记录/评分保持不变 |
| V06 | 旧检查迁移等价 | 覆盖已有 runner 的最小基线/补丁集合，新旧输入、判据、超时与适用范围一致；结果差异逐项解释，不改期望掩盖问题 |
| V07 | 多检查点汇报 | fixture 覆盖三类、多项、组级项和各种状态；空类不算通过；API/页面/导出一致；旧记录 legacy；页面实际渲染/交互验证 |
| V08 | 隐藏与可信评测 | agent 无法读隐藏材料/完整项目/缓存历史/其他运行；公开接口不泄漏；agent 改测试不影响 supervisor 判定 |
| V09 | 旧补丁新检查 | 同一旧补丁/基线运行 fixture suite v1/v2，新增检查确实执行，结果独立且不调用模型；至少一个现存 OCCT 补丁完成导入/应用/现有检查；覆盖不兼容、应用失败和缺报告 |
| V10 | DSH/Codex 协议 | DSH 既有行为兼容；Codex 假 CLI 覆盖结构化事件、截断/畸形输出、usage 缺失、失败/无报告、明确 session 恢复和取消 |
| V11 | 有限恢复 | 限流/断连/拒绝/认证失败/取消/耗尽均按规则；不重置预算、不并发续接、不跨会话，保留首次状态 |
| V12 | 认证与执行边界 | agent shell/构建读不到认证，日志/快照无 secret；不通过则 live disabled；Linux 隔离不降级 |
| V13 | 迁移与仓库卫生 | 备份/迁移/校验/回退可用，原数据不变；旧运行/资产可读；diff 检查通过，无源码副本、数据库、日志、工作区、依赖目录或凭据入仓 |
| V14 | 真实 smoke | 授权后 DSH/Codex 各一项小任务，session/使用量/补丁/评测可追溯；不要求模型一定修复成功 |

最终提供 `docs/acceptance-report.md`：逐项 V01–V14 标记 pass/fail/blocked/not_run，附环境、命令、证据、未完成原因；包含题目迁移映射、源码核验、新旧检查对照、旧补丁新套件结果和回退步骤。

安装未授权时干净环境复现列为待验收；无 Mac 或其他账号时明确实际平台/独立账号部署待实测；付费 smoke 未授权时 V14 待验收。分别报告架构离线完成与真实 live 验证状态，不能用 demo/fixture 替代真实实验，也不能关闭隔离或修改判据来消除未完成项。
