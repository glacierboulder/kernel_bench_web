# 增加 OCCT #29322 几何回归基准：General Fuse 未合并公差内共边

OCCT 自然父提交为 `c5b89fa358ab0932d7edb54af82b86bb4164dd5c`，[上游修复](https://github.com/Open-Cascade-SAS/OCCT/commit/b7cd7c2b7c54cca90dedfa38e7e59f0cc0a0ccd8) 为 `b7cd7c2b7c54cca90dedfa38e7e59f0cc0a0ccd8`。

## 公开输入

题面为 `benchmarks/occt/issues/occt-29322/1/statement.md`。进入该题目录后运行 `DRAWEXE -b -f public/reproduce.tcl`。脚本用 DRAW 命令生成输入，不依赖外部模型文件。

## 几何判据

平行线段原例、平移及三倍缩放均要求一条有效共边和两个顶点。修复前为两条边，总长 20/20/60；修复后为一条边，长度 10/10/30。

正常回归：超出公差的分离线段保留两条有效边、六个顶点，总长 20。

## 验证证据

- `benchmarks/occt/evaluation/provenance/occt29322/` 包含自然 B/F 日志、源码锁来源、参考补丁和冻结检查记录。
- 原例及两个邻域：B 三项均失败，F 三项均通过；正常回归 B/F 均通过。
- [自然 B 日志](natural-B.txt)与[自然 F 日志](natural-F.txt)保留逐例测量值。参考补丁应用后，源码子树与实际构建的自然 F 一致；冻结套件在该 F 上通过 4/4。正式复评单独从锁定的 B 重新应用补丁并编译，是参考补丁的技术验收，不是带 Agent 报告的提交。

冻结题面目录使用 `DRAWEXE -b -f reproduce.tcl` 运行公开输入。四个正式检查入口会将测量异常传给运行器，另行记录脚本错误。[公开命令实测](frozen-public-F.json)

正式离线复评通过原例 1/1、邻域 2/2 和回归 1/1。[复评记录](round-offline.json)
