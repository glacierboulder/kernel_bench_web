# Agent Bench Web

一个按用户账号独立部署的实验框架。程序、公开题库、数据、源码缓存和运行工作区分开管理；题目与评测套件通过版本化 JSON 清单接入。框架当前提供离线演示、只读题库检查、DSH worker 兼容路径和旧补丁独立复评。

Codex CLI 的子进程协议、JSONL 解析和有限的同 session 恢复已有离线假 CLI 覆盖。Codex live 暂时关闭，因为 worker 尚未接入 supervisor-only 推理代理，无法把认证与不可信构建子进程隔离。真实 DSH 任务会调用外部模型并产生费用，执行前需由操作者确认具体模型与预算。演示和 fixture 不代表模型修复能力或 OCCT 正式正确性。

## 快速开始

需要 Python 3.11 和 `requirements.txt` 中的框架依赖。已有 conda 环境可直接激活；创建新环境会安装依赖，应按部署环境的依赖审批流程操作。

```bash
conda activate <your-environment>
python -m backend.catalog
python -m backend.import_proto
python -m backend.doctor
./run.sh
```

服务默认仅绑定回环地址。浏览器访问地址和服务端口由 `BENCH_HOST`、`BENCH_PORT` 或配置文件控制。远程使用时保留回环绑定，通过 SSH 隧道转发；示例见 [部署说明](docs/deployment.md)。

默认题库在 `benchmarks/occt/`，当前包含 5 个新三 issue 组合和 7 个旧题组，共 12 个可独立运行的注册题目。新旧目录规则、issue/suite 路径映射及此次迁移的检查记录见题库中的 [命名映射](benchmarks/occt/NAMING_MAP.md) 和 [迁移验收记录](benchmarks/occt/evaluation/provenance/integration-validation.json)。外部兼容题库可用 `BENCHMARK_ROOT` 配置；历史别名 `BENCH_PROTO_ROOT` 仍受支持。题库通过文件维护，目前没有网页题目编辑器；复制示例和标识更新规则见 [手工维护题库](docs/benchmark-authoring.md)。公开题库校验只依赖 Python 标准库，可在 macOS 上读取清单；Linux 沙箱和编译依赖只用于实际实验。

## 配置与数据

配置优先级为 CLI 参数 > 环境变量 > JSON 配置 > 默认值。配置文件默认位于 `~/.config/agent-bench-web/config.json`，参考 [config.example.json](config.example.json)。路径按配置文件目录解析。敏感认证只通过受控环境注入，不写入题库、运行快照或日志。

默认目录位于仓库外的用户目录：

- data：SQLite、运行记录和资产。
- cache：每账号去重的只读源码基线。
- work：临时任务与部署工作区。

已有仓库内 `data/bench.sqlite3` 的部署会继续使用原目录，直到操作者显式迁移。迁移先 dry run；执行时要求应用和 worker 已停止，使用 SQLite backup API，保留原目录，回退时将配置指回原位置。完整步骤见 [数据迁移](docs/data-migration.md)。本次没有迁移、删除或回滚数据库记录；一次目录导入误用了默认数据库，影响范围无法从缺少的操作前快照中确定，细节见 [验收报告](docs/acceptance-report.md)。

## 题库和源码

题库由 `catalog.json` 引用 issue、题组和评测套件的版本。issue 固定一个 `source_id`；joint 题组要求所有成员使用同一基线。检查点由可信 runner/oracle 注册表执行，支持 original、neighborhood、regression 分类及 public/hidden 可见性。公开 API 只返回公开题面和安全汇总。

源码准备不会自动联网。操作者需提供含锁定 commit 的本地 Git checkout：

```bash
python -m backend.source_cache <source-id> --from-dir <local-git-checkout>
```

工具从本地 Git 对象导出锁定 commit，验证清单中的物化树哈希，再原子发布到用户缓存。没有 Git 元数据的导出只有在明确传入 `--allow-unverified` 且哈希匹配时才会导入，并保持未验证状态。树哈希定义、材料格式和扩展示例见 [题目构造与格式指南](docs/benchmark-authoring.md#清单格式与目录结构)。

## Agent 与评测

DSH 和评测在 Linux bubblewrap 沙箱中分开运行。Agent 只获得锁定源码的独立可写副本、公开题面、复现输入和允许的工具；隐藏评测、宿主 home、凭据、缓存历史和其他运行目录不挂载到 agent。缺少 bubblewrap 或源码验证时不降级为裸执行。

DSH 运行还要求本地锁定 runtime、Node、已验证的隔离条件和受控密钥。数据只记录可观测的 session、使用量和执行结果。代理从标准环境变量读取；模型网关可从环境或配置读取 `http` / `https` 代理，沙箱不继承代理设置。不会用代理扩大 agent 的公网权限。

旧 `proto-1` 记录保持可读。新 catalog 任务在入队时冻结题面、材料、评测套件、工具链和 provenance；源码在运行开始时从锁定缓存复核并复制。Codex 与有限恢复的当前边界列于 [部署说明](docs/deployment.md)。

复评必须显式选择 suite ID 和版本，不调用模型、不改原运行：

```bash
python -m backend.reevaluate --run-id <run-id> \
  --suite-id <suite-id> --suite-version <suite-version>

python -m backend.reevaluate --patch <patch.diff> --source-id <source-id> \
  --suite-id <suite-id> --suite-version <suite-version>
```

补丁复评仅在指定基线检查并应用原补丁，不自动 rebase。无旧报告时仍可执行新版检查，并单独记录报告缺失。

## 开发与验收

所有 Python 测试应在 conda 环境运行；本仓库不声明需要额外测试框架。

```bash
conda activate <your-environment>
python -m unittest discover -s tests -v
node --check frontend/app.js
node --check frontend/studies.js
```

测试不会调用远程模型。`docs/acceptance-report.md` 逐项说明已实现、已验证和仍需真实环境验证的内容；不以离线 fixture 代替付费模型 smoke、跨账号部署或 macOS 实测。

## 主要目录

- `backend/`：配置、catalog、冻结、worker、评测、API 和迁移工具。
- `benchmarks/occt/`：版本化公开题库和 supervisor 评测材料；不含展开的 OCCT checkout 或原始 Git bundle。bundle 与历史运行记录保存在外部归档，项目内清单保留其 SHA256；运行源码仍从本地 Git 对象库准备。
- `schemas/`、`benchmarks/occt/schemas/`：数据契约 JSON Schema。
- `docs/`：部署、题库、迁移和验收说明。
- `runtime/dsh/`：固定 DSH npm 依赖声明和锁文件；不提交 node_modules。
- `tests/`：Python 标准库单元和集成测试。
