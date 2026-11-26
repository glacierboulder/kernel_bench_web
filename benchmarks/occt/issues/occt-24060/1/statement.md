# General Fuse 在方形面的角点保留了重复顶点

在 XZ 平面建立边长 1 的方形面，顶点依次为 `(0,0,0)`、`(0,0,1)`、`(1,0,1)`、`(1,0,0)`，再单独建立位于 `(0,0,1)` 的顶点。把面和该顶点作为两个参数交给 General Fuse。

当前结果通过有效性检查，面积为 1，但同一角点处有两个拓扑顶点。请修复布尔干涉处理，使融合结果保留 4 个唯一顶点、4 条边和 1 个面，独立输入顶点的位置恰有一个拓扑顶点。结果须有效，面积与 1 的绝对误差小于 `1e-7`。

在冻结题面的公开目录运行下列命令。第一个参数是锁定版本的 OCCT 源码路径。Linux x86-64 主机需要 GCC、Ninja、Python 3、GNU binutils、dpkg-deb、xz 和 Tcl 开发头文件。

```sh
bash public-build.sh /path/to/occt /tmp/occt-24060-build
bash public-replay.sh /tmp/occt-24060-build
```
