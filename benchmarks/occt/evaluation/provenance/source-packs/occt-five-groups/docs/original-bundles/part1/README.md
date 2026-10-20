# OCCT 低重合精选bundle

当前catalog仅登记NG-04R-v2与NG-05T-v1：2组、6个issue版本、2套件、2个源码锁，覆盖5个唯一issue。两组只重合M30082（1/3）。选择规则、完整核验与限制见上级README.md、REPORT_ZH.md和audit/。

所有组/issue/suite的版本化定义和测试字节保持原样。仅裁剪catalog、source lock及无关目录；共享源码的provenance已改指向本包保留的NG-05T自含源码bundle及本组参考修复，原provenance归档在上级audit/original_source_provenance/。`evaluation/provenance/NG-04T-v1-evidence/`中唯一的派生补丁是共享源码依赖，不表示保留NG-04T题组。

历史验收证据按原字节保留，可能含原服务器绝对路径和当时完整catalog的快照；这些是审计记录，不是当前的活动题目索引。原始无效运行标记和负控保留，不能把它们误计为有效通过。当前活动题组仅以本目录catalog.json为准。

监督侧evaluation材料、参考补丁和源码派生信息不能通过公开题目接口泄露给代理。完整运行需要兼容的agent_bench_web框架及Clang10/CMake/Tcl工具链；本目录不捆绑生产数据库、凭据、旧agent运行或编译缓存。
