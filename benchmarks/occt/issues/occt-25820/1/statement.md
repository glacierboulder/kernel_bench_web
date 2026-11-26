# 旋转面与平面的布尔截交只留下两个孤立顶点

读取公开模型 `OCC25820-Revolution_5.brep` 与 `OCC25820-Translation_1.brep`。按形体枚举顺序分别取第 4 个面和第 2 个面，使用启用三维曲线逼近的 `BRepAlgoAPI_Section` 求截线。两个输入在一段很短的区间内相交。当前结果仅含两个孤立顶点，总边长为零。

请修复几何求交，使截面形体有效，包含两个顶点和连接它们的一条边。截边长度应为 0.000025 模型单位，允许绝对误差 0.00000001。

在冻结题面的公开目录运行以下命令。第一个参数是锁定版本的 OCCT 源码路径。Linux x86-64 需要 GCC、Ninja、Python 3、GNU binutils、dpkg-deb、xz 和 Tcl 开发头文件。

```sh
bash public-build.sh /path/to/occt /tmp/occt-25820-build
bash public-replay.sh /tmp/occt-25820-build
```
