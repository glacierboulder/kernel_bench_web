# 两个圆柱面片的布尔公共区域为空

读取公开模型 `bug25163_qf_25_39.brep`，按照形体枚举顺序取其中两个面，执行 Boolean Common。当前结果是空复合体，模型中相互覆盖的区域被丢弃。请修复求交中圆柱面上参数曲线的周期定位。

期望公共区域包含 4 个顶点、4 条边和 1 个面，通过形体有效性检查，面积约为 3417.71 平方模型单位，绝对误差允许 0.1。

在冻结题面的公开目录运行下列命令。第一个参数是锁定版本的 OCCT 源码路径。Linux x86-64 主机需要 GCC、Ninja、Python 3、GNU binutils、dpkg-deb、xz 和 Tcl 开发头文件。

```sh
bash public-build.sh /path/to/occt /tmp/occt-25163-build
bash public-replay.sh /tmp/occt-25163-build
```
