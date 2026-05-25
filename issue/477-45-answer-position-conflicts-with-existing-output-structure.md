# `477-45` 的 `answer_position` 与现有输出结构冲突

## 背景

- dataset: `spreadsheetbench_verified_400`
- task-id: `477-45`
- 关联 run-id:
  - 基线通过：`codex-gpt-5-5-verified400-all-20260523-230050`
  - cellData prompt 全量失败：`codex-gpt-5-5-verified400-all-20260525-153934`
  - wrong77 重跑失败：`codex-gpt-5-5-verified400-wrong77-rerun1-20260525`

题目要求按 A/B/C 三列合并重复项，并对 `Total` 求和，结果从 `G2` 开始输出。`answer_position` 标为 `G1:I1000`，但工作簿已有目标表头是 `G:J = ID, Brand, type, Total`，golden 也实际在 `G:J` 中保存四列结果。

## 现象

三次运行的题面和 `answer_position` 一致，但结果不同：

- 基线 run 读取 `A2:D1000`，按 `ID, Brand, type` 分组并求和，写入 `G:J` 四列。虽然越过 `answer_position`，但 `G:I` 内与 golden 一致，因此评测通过。
- cellData prompt 全量 run 严格遵守 `G1:I1000`，将 `Brand/type` 合并到一列，并把 `Total` 放在 I 列，导致 `G:I` 列结构变成 `ID, Brand/type, Total`，评测失败。
- wrong77 重跑同样严格限制在 `G:I`，将三列 key 压缩为两列并保留 `Total`，仍然失败。

golden 的实际结构：

```text
G1:J1 = ID, Brand, type, Total
G2:J2 = AA, ASD1, LG1, 33300
G3:J3 = BB, ASD2, LG2, 143856
G4:J4 = CC, ASD3, LG3, 114219
```

评测只比较 `G:I`，因此能通过的关键是 `G:I = ID, Brand, type`；`Total` 实际位于 `answer_position` 外的 J 列。

## 根因判断

这不是值类型问题，也不是 `ICellData` 写入本身造成的错误。根因是 `answer_position`、任务要求、现有表头、golden 输出结构之间不一致：

- `answer_position` 只有三列，无法同时容纳 `ID`、`Brand`、`type`、`Total` 四个语义列。
- 工作簿和 golden 都暗示正确输出范围应为 `G:J`。
- 当前 prompt 中“只修改 `answer_position`”的强约束，在这个坏标注 case 上压过了工作簿真实结构，诱导 agent 压缩列结构。

## 影响

- `477-45` 在基线为通过，cellData prompt 后两次稳定失败，表现为一次稳定回退。
- 如果只看评测结果，容易误判为 cellData / 值类型提示词引入回归；逐日志和 workbook 对比后，实际是范围标注冲突被更严格的范围遵守放大。

## 候选处理方向

1. 将 `477-45` 记录为数据/题目歧义或 `answer_position` 标注问题，逐题分析时不要归因给值类型提示词。
2. 后续如果调整通用 prompt，需要谨慎处理“answer_position 与现有目标表头明显冲突”的场景：可以要求先报告冲突并优先保持表格语义结构，但不能鼓励 agent 随意越界写入。
3. 如果要修数据，应把 `answer_position` 改为覆盖 `G1:J1000`，或调整题目/模板使三列范围内的预期结构明确。

## 证据位置

- `.runs/univer-agent/codex-gpt-5-5-verified400-all-20260523-230050/tasks/477-45/logs/`
- `.runs/univer-agent/codex-gpt-5-5-verified400-all-20260525-153934/tasks/477-45/logs/`
- `.runs/univer-agent/codex-gpt-5-5-verified400-wrong77-rerun1-20260525/tasks/477-45/logs/`
- `report/codex-gpt-5-5-verified400-all-20260523-230050.json`
- `report/codex-gpt-5-5-verified400-all-20260525-153934.json`
- `report/codex-gpt-5-5-verified400-wrong77-rerun1-20260525.json`
