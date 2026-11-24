# OCCT #30092 同域顶点附近的布尔截线无效且长度偏大

先按上游输入切分曲面，再计算 FF 与 EF 干涉形成的截线。上游修复更新了带同域顶点的 pave block，并移除两端为同一顶点的退化短边。原例应得到 5 个顶点、4 条边，截线总长约 1250.44。邻域分别整体平移操作数与将短线段半长从 0.2 调至 0.21。健康对照使用两个正交矩形，截线为长度 20 的直边。[上游修复](https://github.com/Open-Cascade-SAS/OCCT/commit/241a61330adaa27e2c2be65b29ea5075cbf57413)

B 为 `798a95ed9b104d612e87433dc5dd7527f5a62ead`，F 为 `241a61330adaa27e2c2be65b29ea5075cbf57413`。

模型 `bug26795_c.brep` 来自 OCCT 7.5.0 发布的测试数据集。镜像首次导入提交为 `12ec0ea9af6db153903fe0cf57ff5c4f30f66830`，文件 Git blob 为 `705021c5db2139b417eccfc540b8d979f5abe641`，SHA-256 为 `7cbbab46307154bb1f8d3dc14738263fac8b1c7d29d107aaba6653b290c838af`。镜像的说明列明来源，未列出单独的模型许可条款。[官方数据集公告](https://occt3d.com/dev/content/open-cascade-technology-testing-dataset-published/) · [原始文件](https://github.com/a-betenev/opencascade-dataset/blob/12ec0ea9af6db153903fe0cf57ff5c4f30f66830/brep/bug26795_c.brep)

正式离线复评通过原例 1/1、邻域 2/2 和回归 1/1。[复评记录](round-offline.json)
