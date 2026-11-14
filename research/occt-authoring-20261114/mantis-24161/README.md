# 24161 候选题提交包

Windows 本地复核通过。基线为派生 OCE 提交 5434272be3eecaf06f0921f8fa4f1a6df7672033。从该提交构建 TKGeomAlgo，再单独应用 reference.patch 重新构建。两侧使用同一套已有 DRAW 运行依赖。

原例、平移和旋转在 B 均达 45 秒外层时限，在 F 均完成并通过有效性、单实体及体积检查。普通融合回归在两侧均通过。见 evidence/rebuilt-results.json 和对应日志。脚本由外层限时，要求退出码 0 且恰有一条 CASE_PASS。

此包可提交供人工审阅。现有默认 Linux 构建器不支持该 6.6 系列派生基线，正式评测接入仍需验证。45 秒是本机观测上限。

公开脚本已用重新构建的 Windows F 验证仓库布局和扁平布局。参考补丁已对锁定基线的原始文件执行无忽略选项的 git apply --check。

## Linux 原生重放已完成

从相同源码基线配置 DRAWEXE 与 TKTopTest，B/F 共用 locale 兼容头、窄化选项、保留空值检查选项以及 fsqrt 内部函数改名。F 在此基础上应用 reference.patch。B 原例、平移和旋转均在 45 秒后终止，正常回归通过；F 四项均返回一条 CASE_PASS。原始日志与配置证据见 evidence/linux。此处是 Linux 原生重放，默认评测流程的源码缓存与冻结沙箱还未验证。
