# 15387 dynamic array export repro

## 目的

复现 `Sheet1!A13:A14` 动态数组 spill 在 Univer 内可见，但导出后的 xlsx 只有 anchor 单元格缓存值的问题。

## 本地文件引用

- 输入 `.univer`: `.runs/univer-agent/codex-gpt-5-5-verified400-all-20260526-231834/15387/task/cases/case_1/input.univer`
- 已导出 output: `.runs/univer-agent/codex-gpt-5-5-verified400-all-20260526-231834/15387/task/outputs/case_1/output.xlsx`
- golden: `data/spreadsheetbench_verified_400/spreadsheet/15387/1_15387_golden.xlsx`
- agent 脚本: `.runs/univer-agent/codex-gpt-5-5-verified400-all-20260526-231834/15387/task/work/case_1_edit.js`

## 复现命令

```bash
univer run .runs/univer-agent/codex-gpt-5-5-verified400-all-20260526-231834/15387/task/cases/case_1/input.univer --file .runs/univer-agent/codex-gpt-5-5-verified400-all-20260526-231834/15387/task/work/case_1_verify.js
univer export .runs/univer-agent/codex-gpt-5-5-verified400-all-20260526-231834/15387/task/cases/case_1/input.univer /tmp/15387-output.xlsx --json
python3 ai-analyze/codex-gpt-5-5-verified400-all-20260526-231834/repro/15387/check_answer_range.py /tmp/15387-output.xlsx data/spreadsheetbench_verified_400/spreadsheet/15387/1_15387_golden.xlsx
```

## 实际/期望

- 期望：导出后的 xlsx 用 `openpyxl.load_workbook(..., data_only=True)` 读取 `A13:A14` 为 `["A", "D"]`。
- 实际：当前 run 的 output 读取为 `["A", None]`，`A14` spill 缓存缺失。

