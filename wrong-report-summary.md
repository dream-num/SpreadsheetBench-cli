## 评测程序问题，应该报issue，详见evaluation-dataset-quality-bugs.md（4）

- **130-9**: sheet 名内逗号被误拆。
- **283-32**: 整列范围 `A:G` 解析失败。
- **49300**: 前导 NBSP 导致 sheet 名不匹配。
- **45944**: 多 range 逗号后空格导致 range 解析失败.

## 数据集问题，应该报issue，详见evaluation-dataset-quality-bugs.md（1）
- **42930**: golden 文件名 id 错位导致旧评测发现不到 case.

## 题目/示例问题，不应该修复（6）

- **50486**：通过率:从未通过。原因：prompt 明确要求显示 Chep/Loscam；agent 日志中识别大小写冲突后按题面写入 Chep/Chep/Loscam/Loscam，答案为 CHEP/CHEP/LOSCAM/LOSCAM，差异仅大小写。
- **13284**：通过率:从未通过。原因：题面明确要求只考虑 `Streets!C` 和 `Streets!D` 都有值的行；agent 按此排除了空 End 行，`Base!E5/E8/E10/E13/E16` 为空。答案却把这些源表空 End 行改成有效范围（如 9999 或单点范围），期望返回 Sonia/Mariza/Marcy/Carlos/Fontana，与题面冲突。
- **56915**：通过率:从未通过。原因：题目要求填充/修复 COVER!B18:E23 整个范围，但实际表格中 B19:E20 对应的是 COST OF GOODS SOLD、STUFF 两个分组/结构行，DATA 表对应行也不像真实数据明细行；agent 选择只修复有实际数值语义的 B18:E18 和 B21:E23，并将 B19:E20 保留为空；答案要求 B19:E20 也填入公式并按空源单元格自然结果缓存为数值 0，因此评测失败。
- **486-17**：通过率:从未通过。原因：output 与 golden 在 Blad1!B2:B130 仅 3 处不一致：源数据 A99:A101 混入重复表头 Datum verzending，agent 将其视为非 0yyyymmdd 日期值并在 B99:B101 留空；golden 按宏式固定字符截取，期望 atum  v er。agent的处理方式我觉得更加友好。
- **48643**：通过率:低。原因：agent只做最小修改，在公式扩展时只填充了有实际数据的区域，agent做法也没有问题.
- **56953**：通过率:极低，原因：题面与表格数据存在歧义：题面明确说 row 2 为表头、下方为 numerical values，但表格数据有二级表头，答案文件是保留了二级表头。但agent大多数情况下遵循题目要求，没有保留二级表头。题目描述问题。

## 题目/示例问题，极低修复价值(2)
- **52305**：通过率:从未通过。原因：表格数据误导，题目要求按两项 criteria：Name + time range 计数，但表内 I3=155、K3=Reg 和 first three criteria 表述误导 agent 额外加入 Destination/Type，答案公式只按 Name + MOD(Time,1) 计数。
- **43436**：通过率:从未通过。原因：题面同时写“by the end of each month”和“not closed before the first day of the month”，两者口径冲突；答案按月末仍 open，agent 常按月内曾 open 统计。

## 题目/示例问题，低修复价值(1)
- **37900**：通过率:不稳定。原因：题目只说根据 current day's date 返回值，但源表没有对应匹配项，题目也未说明匹配规则；agent 选择同月返回 5000 不能算错，答案使用vlookup模糊匹配。
