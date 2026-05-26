# 49300 answer_position 前导 NBSP 导致评测误失败

## 问题描述

`spreadsheetbench_verified_400` 的 task `49300` 在 `dataset.json` 中 `answer_position` 为：

```text
\u00A0'Sheet1'!C2:C3
```

首字符是 NBSP (`\u00A0`)。当前 `evaluation/evaluation.py` 解析 sheet 名时只执行 `lstrip("'").rstrip("'")`，不会移除 NBSP，导致 sheet 名被解析为 `"\u00A0'Sheet1"`，从而判定 worksheet not found。

## 影响

该问题会让评测失败与 agent 输出无关。用当前正式评测逻辑直接比较 golden 与 golden，也会失败；去掉前导 NBSP 后，同一 output 可通过评测。

## 复现与验证

原始 `answer_position`：

```text
"\xa0'Sheet1'!C2:C3"
```

用真实 `evaluation.evaluation.compare_workbooks()` 复现：

```text
golden vs golden: (False, '')
golden vs golden with strip: (True, '')
```

临时将 `answer_position` 改为：

```text
'Sheet1'!C2:C3
```

然后只跑单题评测：

```bash
cd evaluation
EVALUATION_MODEL='gpt-5.5' ../.venv/bin/python3 evaluation.py \
  --dataset spreadsheetbench_verified_400 \
  --setting univer_agent \
  --task-id 49300 \
  --run-id tmp-49300-answer-position-strip-20260526
```

结果：

```json
{
  "id": 49300,
  "test_case_results": [1],
  "soft_restriction": 1.0,
  "hard_restriction": 1
}
```

临时数据修复已回退，`dataset.json` 保持原始状态。

## 根因判断

归因类型：数据标注 / 评测解析缺陷。

不是 agent 输出值错误，也不是 `univer-cli` 导出问题。按 `data_only=True` 读取时，当前 output 与 golden 在 `Sheet1!C2:C3` 的值均为：

```text
C2 = 35
C3 = 37
```

## 候选修复方向

- 数据层：清理 `dataset.json` 中 `answer_position` 的前后不可见空白字符。
- 评测层：解析 `answer_position` 时对 `sheet_name` 和 `cell_range` 做 `strip()`，并显式处理 NBSP (`\u00A0`)。

