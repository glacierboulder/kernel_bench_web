# Windows 本地数值检查兼容

旧 MSVC DRAW 的浮点异常陷阱会使 Tcl 的 string is double／expr 数值解析异常退出。作者在 B/F 同时加载 benchfpe 扩展屏蔽陷阱后重跑所有标准断言；不修改内核源代码或几何阈值。用 MSVC 编译 benchfpe.cpp 为 benchfpe.dll，然后在作者 wrapper 开始处执行 `load <dll> Benchfpe`。该审计兼容扩展不注册到框架、不随题目发给模型，也不能代替 Linux 重放。
