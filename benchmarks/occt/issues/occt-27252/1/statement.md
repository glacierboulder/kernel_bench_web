# Mantis #27252 — cylinder and plane intersection

公开原例检查圆柱面与平面的交线数量和容差。B 的官方 Tcl 在无 3D 曲线时会因 NbCurv 未定义提前退出；监督 runner 只识别官方输出中的精确无曲线签名，并保留 oracle 已运行与 Tcl source 返回码。

请提交 `patch.diff` 和 `report.md`。
