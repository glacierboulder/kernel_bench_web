# 圆角交线使用错误曲面边界，导致边容差膨胀

读取公开的 OCC615.brep，按 DRAW 的 `explode a e` 顺序在第 15 条边构造半径 9 mm 的有理圆角。结果必须有效，有 14 个面，面积 197055.036 mm²（绝对误差 < 0.2 mm²），边界各子形最大容差不得超过 0.001 mm。原例另输出上游明确指出的第 21 条结果边及其顶点的最大容差。不能以单纯调高存储容差代替正确的几何交线。

在冻结公开目录中，先准备本题对应源码和空构建目录：`bash public-build.sh "$OCCT_SOURCE" "$OCCT_BUILD" "$PWD"`。在同一目录运行 `bash public-replay.sh "$OCCT_BUILD"`。环境为 Linux x86-64，需 GCC/G++、Python 3、Tcl 开发头、Ninja、tar、xz、dpkg-deb。历史 CDL 生成工具已随题冻结，构建不需联网。所有长度按 mm，面积按 mm²。
