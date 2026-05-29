# evaluation / dataset 质量问题导致无效评测信号

## 概要

`spreadsheetbench_verified_400` 中存在一组与 agent 输出无关的评测/标注/数据文件问题。其中 4 个 task 直接把 golden 答案作为 output 交给正式 `evaluation/evaluation.py` 评测仍失败：

```text
283-32, 130-9, 49300, 45944
```

另有 1 个 task 曾因 golden 文件命名与 task id 不一致，旧评测程序发现不到 case，导致 `test_case_results: []` / `NOT_RUN`：

```text
42930
```

正式 direct-golden 评测报告：

```text
outputs/eval_directgold_goldbug_tmp-gold-direct-20260529-verified400.json
```

复核结果：

```text
report_rows=400
report_fail_count=4
report_fail_ids=283-32,130-9,49300,45944
```

这说明这些失败或未执行状态至少在对应评测程序版本下没有有效 agent 复测信号。逐题分析时不要把这些 case 的 FAIL/NOT_RUN 直接归因给 agent 或 `univer-cli` 输出。

## 根因模式一：answer_position 解析

当前 `evaluation/evaluation.py` 中的 `compare_workbooks()` 对 `answer_position` 的解析过于简单：

```python
sheet_cell_ranges = answer_position.split(',')
```

随后只用：

```python
sheet_name = sheet_name.lstrip("'").rstrip("'")
cell_range = cell_range.lstrip("'").rstrip("'")
```

这会遗漏以下合法或现实存在的 `answer_position` 形态：

- 引号内 sheet 名包含逗号。
- 多 range 分隔符后带普通空格。
- 前后带 NBSP (`\u00A0`) 等不可见空白。
- 使用整列范围，例如 `A:G`。

此外，`parse_cell_range()` 只支持 `A1:AB12` 这种显式行号范围，不支持整列范围。

## 根因模式二：golden 文件发现依赖 task id 命名

旧版 `evaluation.discover_case_indices()` 只查找：

```text
*_<task_id>_answer.xlsx
*_<task_id>_golden.xlsx
```

如果 task 目录中 golden 文件存在但文件名里的 id 写错，评测会发现不到任何 case，并写出空的：

```json
"test_case_results": []
```

这会在后续报告中表现为 `NOT_RUN`，而不是 agent 真实失败。

## 已确认问题 task

### 130-9: sheet 名内逗号被误拆

`answer_position`：

```text
'b2b, sez, de'!A5:V10
```

sheet 名本身包含逗号。当前 `answer_position.split(',')` 会把一个合法的 sheet-qualified range 拆成多个片段，后续把 `"'b2b"` 当作单元格/范围解析。

golden-vs-golden 直接复现：

```text
ValueError: b2b is not a valid coordinate or range
```

人工绕过错误拆分后，直接比较 `b2b, sez, de!A5:V10`，golden-vs-golden 通过。

历史补充：部分旧 run 另有 agent 内容错误，把 `cdnr!E` 的单据类型 `C` 写到目标 E 列；但 direct-golden 复现证明当前这个 FAIL 形态本身是评测解析问题。

### 283-32: 整列范围 `A:G` 解析失败

`answer_position`：

```text
Sheet3'!A:G,'Sheet4'!A:G
```

当前 `parse_cell_range()` 解析 `A:G` 时，起止行号为空字符串，执行 `int('')` 抛错。

golden-vs-golden 直接复现：

```text
ValueError: invalid literal for int() with base 10: ''
```

将范围临时规范化为：

```text
'Sheet3'!A1:G2,'Sheet4'!A1:G2
```

后，golden-vs-golden 通过。该 task 的 golden 工作表中 `Sheet3` 和 `Sheet4` 当前使用范围都是 2 行、7 列。

### 49300: 前导 NBSP 导致 sheet 名不匹配

`answer_position`：

```text
\u00A0'Sheet1'!C2:C3
```

首字符是 NBSP (`\u00A0`)。当前 evaluator 不会 trim NBSP，sheet 名被解析为带 NBSP/引号残留的字符串，导致 worksheet not found。

golden-vs-golden 直接结果：

```text
COMPARE_FALSE
```

去掉前导 NBSP 后：

```text
'Sheet1'!C2:C3
```

golden-vs-golden 通过。

### 45944: 多 range 逗号后空格导致 range 解析失败

`answer_position`：

```text
G4:G6, G11:G13, G20:G22
```

当前 evaluator 按逗号拆分后没有 trim 普通空格，第二段变成 `" G11:G13"`。`generate_cell_names()` 生成带前导空格的坐标，openpyxl 返回 tuple，后续访问 `.value` 报错。

golden-vs-golden 直接复现：

```text
AttributeError: 'tuple' object has no attribute 'value'
```

去掉逗号后的空格后：

```text
G4:G6,G11:G13,G20:G22
```

golden-vs-golden 通过。

### 42930: golden 文件名 id 错位导致旧评测发现不到 case

task 目录和 input 文件命名正确：

```text
data/spreadsheetbench_verified_400/spreadsheet/42930/
data/spreadsheetbench_verified_400/spreadsheet/42930/1_42930_init.xlsx
```

但 golden 文件名里的 task id 写成了 `43930`：

```text
data/spreadsheetbench_verified_400/spreadsheet/42930/1_43930_golden.xlsx
```

旧版 `discover_case_indices()` 只按 task id 匹配 `*_<task_id>_golden.xlsx`，因此对 `42930` 发现不到 case，并输出：

```json
"test_case_results": []
```

这不是 agent 没有输出，也不是 output 与 golden 值不一致，而是数据文件命名与评测路径发现逻辑不兼容。

该问题已有评测层 fallback 修复记录：

```text
fix-logs/2026-05-29-evaluation-golden-filename-fallback.md
```

修复后，`discover_case_indices()` 在标准 task-id-specific 文件名找不到时，会回退到 task 目录内唯一的 `case_index_*_answer.xlsx` / `case_index_*_golden.xlsx`；`get_ground_truth_path()` 也做同类 fallback。验证结果中，`42930` 从 `test_case_results: []` 变为 `test_case_results: [1]`。

## 候选修复方向

评测层应优先修通用 parser 和路径发现逻辑，而不是对 task id 特判：

1. 解析 `answer_position` 时只在引号外逗号处分隔 range。
2. 对每个 range 片段做 `strip()`，并显式处理 NBSP，例如先把 `\u00A0` 视为普通空白。
3. sheet 名解析应识别标准 quoted sheet name，而不是只 `lstrip("'").rstrip("'")`。
4. 支持整列范围 `A:G`。候选展开范围可使用 `max(ws_gt.max_row, ws_proc.max_row)`，避免漏掉 output 多写的污染行，同时避免展开到 Excel 最大行导致性能问题。
5. 标准 golden/answer 文件名优先；如果缺失，可回退到 task 目录内唯一匹配的 `case_index_*_golden.xlsx` / `case_index_*_answer.xlsx`，并在报告或日志中保留 fallback 信息。
6. 评测主循环不应吞掉所有异常后只写 `[0]`；至少在 debug/report 中保留异常类型和消息，方便区分 agent 输出错误、evaluator 自身错误、数据命名问题和真实未执行。

## 建议测试

新增 golden-vs-golden regression tests，覆盖：

- quoted sheet name 中含逗号：`'b2b, sez, de'!A5:V10`
- 普通多 range：`G4:G6, G11:G13, G20:G22`
- 前导 NBSP：`\u00A0'Sheet1'!C2:C3`
- 整列范围：`'Sheet3'!A:G,'Sheet4'!A:G`
- 既有正常范围：`A1:B2`、`'Sheet1'!C2:C3`
- golden 文件名 task id 错位但 task 目录内唯一匹配：`42930/1_43930_golden.xlsx`

## 处理口径

在修复 evaluator 或数据标注前：

- `130-9`、`283-32`、`49300`、`45944` 应按 `answer_position` 评测/数据问题处理。
- `42930` 应按 golden 文件命名/路径发现数据问题处理；在包含 fallback 的当前评测版本中可重新纳入正常评测。
- 逐题分析这些 task 时，先做 direct-golden 或规范化范围复核。
- 不应把 direct-golden 都失败或旧评测发现不到 case 的现象计入 agent prompt、`univer-cli` 或 workbook 编辑策略的真实退化。
