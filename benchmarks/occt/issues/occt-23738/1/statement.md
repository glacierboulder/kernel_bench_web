# 近轴二次曲面的布尔融合没有连接相交部分

对公开的两个 BREP 做 Fuse。父版生成两个彼此分离的壳，面积仍接近上游参考值。请修复求交与布尔分割，使这两个相交输入在该版本返回一个连通的壳。

按历史测试，结果应是一个复合形，含 8 个顶点、12 条边、8 个线框、6 个面、1 个壳和 0 个实体。形体应通过 BRep 有效性检查，面积与 225009 的绝对误差小于 1。

可在题面旁的冻结公开目录或题库目录的 `public/` 运行下面两条命令。Linux x86-64 主机需要 GCC、Ninja、Python 3、GNU binutils、dpkg-deb、xz 与 Tcl 开发头文件。公开包带有离线生成工具、许可证和源文件清单。

```sh
bash public-build.sh /path/to/occt /tmp/occt-23738-build
bash public-replay.sh /tmp/occt-23738-build
```
