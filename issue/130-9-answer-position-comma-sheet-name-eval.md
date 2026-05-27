# 130-9 answer_position 逗号 sheet 名评测解析失败

## 问题

task 130-9 的 `answer_position` 为：

```text
'b2b, sez, de'!A5:V10
```

sheet 名本身包含逗号。当前 `evaluation/evaluation.py` 在 `compare_workbooks()` 中使用：

```python
sheet_cell_ranges = answer_position.split(',')
```

这会把一个合法的 sheet-qualified range 误拆成多个片段，导致后续把 `"'b2b"` 当作单元格/范围解析。

## 最小复现

直接用 golden 文件同时作为 ground truth 和 processed file：

```bash
python3 - <<'PY'
import sys, types
m = types.ModuleType('tqdm')
m.tqdm = lambda x, *a, **k: x
sys.modules['tqdm'] = m
sys.path.insert(0, 'evaluation')
from evaluation import compare_workbooks

golden = 'data/spreadsheetbench_verified_400/spreadsheet/130-9/1_130-9_golden.xlsx'
answer_position = "'b2b, sez, de'!A5:V10"
print(compare_workbooks(golden, golden, 'Sheet-Level Manipulation', answer_position))
PY
```

实际结果：

```text
ValueError: b2b is not a valid coordinate or range
```

在正式 `evaluation()` 流程中该异常会被外层 `except` 捕获并记为 `False`，因此即使 output.xlsx 与 golden.xlsx 完全一致，`test_case_results` 仍会是 `[0]`。

## 已核查现象

- 最新单题重跑 `codex-gpt-5-5-verified400-wrong55-rerun-w10-20260527-152344` 的 `130-9/task/outputs/case_1/output.xlsx` 在 `b2b, sez, de!A5:V10` 内与 golden 的 `data_only=True` 值一致。
- 当前 `data/spreadsheetbench_verified_400/outputs/univer_agent_gpt-5.5/1_130-9_output.xlsx` 在同一范围内也与 golden 值一致。
- 部分历史 run 另有 agent 内容错误：把 `cdnr!E` 的单据类型 `C` 写到目标 E 列，导致 `E7:E9` 错为 `C`；正确值应来自 `cdnr!I`，即 `5780.83`、`24059.15`、`12212.82`。

## 根因

评测器没有按 Excel A1 引用语法解析 `answer_position`，而是直接按逗号拆分。逗号出现在单引号包裹的 sheet 名中时，不应作为多 range 分隔符。

## 建议

将 `answer_position` 拆分逻辑改为只在引号外逗号处分隔，或使用能识别 quoted sheet name 的 A1 range parser。修复后应新增 golden-vs-golden 复现用例，覆盖：

- `'b2b, sez, de'!A5:V10`
- 普通多 range，如 `Sheet1!A1:B2,Sheet2!C1:D2`
- 带单引号但不含逗号的 sheet 名

