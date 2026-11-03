# OCCT 二十道单 issue 扩充证据

20 道题目已完成资格校准和正式冻结回放。160 条 B/F 检查全部执行，F 的 80 条必需检查全部通过，20 个 B 原例均复现缺陷，61 个参考侧负对照全部被拒绝。

- [最终报告](../../CADAI/tmp/kernel_bench_web_report/occt_single20_authoring_20261103.md)
- [题目映射](registered-tasks.json)
- [逐检查点矩阵](qualification-matrix.json)
- [候选决策](candidate-decisions.json)
- [输入去重](final-input-deduplication.json)
- [补充输入合法性](supplementary-input-legality.json)
- [完整证据归档身份](evidence-archive.json)

各题 provenance 中的 `evidence.json` 保存可直接审阅的 B/F 及负对照结果。矩阵的 `result_path` 指向证据归档内的 `jobs/` 路径。完整输入、评分快照和原始日志保存在 `evidence/occt-single20-evidence-20261103.tar.gz`。`candidate-prototypes/` 保存未准入原型，重放时按各原 case plan 的路径放入校准端 `single20/` 工作目录，并使用相应共享 helper。

M33639 采用较早自然工作版本作为正几何参考。具体依据、因果修复缺口、数值测量边界和相关题目关系均在最终报告中记录。
