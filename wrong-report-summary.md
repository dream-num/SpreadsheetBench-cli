## 评测程序问题，应该报issue，详见evaluation-dataset-quality-bugs.md（4）

- **130-9**: sheet 名内逗号被误拆。
- **283-32**: 整列范围 `A:G` 解析失败。
- **49300**: 前导 NBSP 导致 sheet 名不匹配。
- **45944**: 多 range 逗号后空格导致 range 解析失败.

## 数据集问题，应该报issue，详见evaluation-dataset-quality-bugs.md（1）
- **42930**: golden 文件名 id 错位导致旧评测发现不到 case.

## 题目/示例问题，不应该修复（4）

- **50486**：通过率:0/5。原因：prompt 明确要求显示 Chep/Loscam；agent 日志中识别大小写冲突后按题面写入 Chep/Chep/Loscam/Loscam，答案为 CHEP/CHEP/LOSCAM/LOSCAM，差异仅大小写。
- **56915**：通过率:0/5。原因：题目要求填充/修复 COVER!B18:E23 整个范围，但实际表格中 B19:E20 对应的是 COST OF GOODS SOLD、STUFF 两个分组/结构行，DATA 表对应行也不像真实数据明细行；agent 选择只修复有实际数值语义的 B18:E18 和 B21:E23，并将 B19:E20 保留为空；答案要求 B19:E20 也填入公式并按空源单元格自然结果缓存为数值 0，因此评测失败。
- **486-17**：通过率:0/5。原因：output 与 golden 在 Blad1!B2:B130 仅 3 处不一致：源数据 A99:A101 混入重复表头 Datum verzending，agent 将其视为非 0yyyymmdd 日期值并在 B99:B101 留空；golden 按宏式固定字符截取，期望 atum  v er。agent的处理方式我觉得更加友好。
- **48643**：通过率:1/5。原因：agent只做最小修改，在累计财富公式扩展时只填充了有实际数据的区域，我觉得agent做法也没有问题.