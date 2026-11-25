# 模型来源

上游工单 #30354 的 DRAW 测试从模型集合中取出 `bug30354_Face_14.brep` 和 `bug30354_vol_neg.brep`。本题使用同一对输入，复现 `tests/bugs/modalg_7/bug30354` 中的截面判据。另一条上游测试 `tests/lowalgos/intss/bug30354` 使用同一曲面和实体的第五个面检查底层交线。模型取自 [公开数据集的固定版本](https://github.com/a-betenev/opencascade-dataset/tree/d78a7a9e6de57699261fa03641ec1b5bafac39a1/brep)。

| 文件 | Git blob | 字节数 |
| --- | --- | ---: |
| bug30354_Face_14.brep | a00c4969824aaa5bdd281d4a9cbf26c5cc2a0552 | 11496 |
| bug30354_vol_neg.brep | c5502d6105a22388da20cd130a450e62c066a787 | 1741 |
