# 20260525 两次 Codex 全量报告错题分析汇总

## 范围

- run 1: `codex-gpt-5-5-verified400-all-20260525-153934`
- run 2: `codex-gpt-5-5-verified400-all-20260525-223740`
- 数据集: `spreadsheetbench_verified_400`
- 模型: `gpt-5.5`
- 分析目录:
  - `ai-analyze/codex-gpt-5-5-verified400-all-20260525-153934/`
  - `ai-analyze/codex-gpt-5-5-verified400-all-20260525-223740/`

## 覆盖情况

| run-id | eval 失败/超时/缺评测项 | 已知原因跳过 | 本次逐题报告 |
| --- | ---: | ---: | ---: |
| `codex-gpt-5-5-verified400-all-20260525-153934` | 60 | 10 | 50 |
| `codex-gpt-5-5-verified400-all-20260525-223740` | 64 | 9 | 55 |

已知原因跳过题：

- 固定已知题目: `262-17`, `283-32`, `42930`
- issue 296 动态数组 / FILTER 导出问题: `220-7665`。仅 `153934` 失败。
- issue 297 空 `<fill/>` 导出后 openpyxl 无法读取: `193-51090`, `215-3911`, `258-35742`, `315-52541`, `332-55060`, `384-57989`

## 运行统计

| run-id | accuracy | total_case_count | correct | error | timeout |
| --- | ---: | ---: | ---: | ---: | ---: |
| `20260525-153934` | 0.8521 | 399 | 340 | 58 | 1 |
| `20260525-223740` | 0.8421 | 399 | 336 | 59 | 4 |

## 主要结论

大多数错题主因仍是 agent 自身的题意理解、范围边界、公式形态和验证不足。典型表现包括：

- 只根据 prompt 前几行样例推断真实数据范围，漏掉完整 used range，例如 `133-38074`, `288-44628`, `131-34033`。
- 把需要公式的任务写成静态值，导致显示值接近但公式模型失败，例如 `180-49300`, `217-5835`, `300-50486`, `309-51680`, `313-52305`。
- 对排序、压缩筛选、行删除/上移、区间边界和布尔条件理解错误，例如 `3-22-47`, `4-23-24`, `174-48975`, `284-43436`, `292-45944`。
- 验证范围过窄，只验证前几行或值缓存，没有验证完整 answer_position、公式文本、格式和导出后的 xlsx，例如 `169-48643`, `185-50193`, `328-54667`。
- 对日期、空值、0、文本 `"-"`、数字格式和样式保留处理不稳，例如 `95-398-14`, `108-486-17`, `255-33157`, `266-37462`, `291-45738`。

## CLI / API / Skill 相关问题

本次新发现或重复出现的工具链相关线索主要有三类：

- 导出兼容风险：`207-54590` 报告中记录 `output.xlsx` 条件格式 XML 可能导致 openpyxl 无法读取；该题同时存在 agent 公式逻辑错误，因此不是纯工具链单因。
- 导出后结构/内容缺失风险：`278-41978` 中 output 目标区域为空且结构缩小，偏向 `univer-cli` 导出或结构保留问题，agent 也缺少导出后验证。
- CLI 参数易误用：多题日志出现 `univer export --overwrite` 误用后恢复，例如 `47-130-9`, `49-146-49`, `245-32023`。这类问题通常没有直接造成最终失败，但说明 skill/prompt 可以更明确提示 `export` 的真实参数形态。

## 环境和超时

`223740` 比 `153934` 多 3 个 timeout，超时案例集中在 agent 反复 API 探测、重连、样式/公式验证或导出前未及时停止：

- `61-203-15`: 300 秒超时，日志显示结果接近完成但卡在重连/验证阶段，未导出。
- `62-208-20`: 300 秒超时，卡在 cellData/公式探测后未完成写入导出。
- `106-448-11`: output 与 golden 基本一致，但外部 agent 进程 300 秒超时导致失败。
- `327-54638`: 反复样式/API 探测导致超时，同时公式范围也与 golden 不一致。

## 数据 / 题目 / 评测歧义

以下题目更适合单独标注为数据或评测口径风险，不应简单归为 agent 能力问题：

- `100-414-20`: answer_position 与 golden 需要的结构移动冲突，严格遵守 answer_position 会无法让 `Invoice No.` 上移到 A1。
- `108-486-17`: 题面说无表头但数据中混入表头；golden 对异常文本执行机械截取，和自然语义不一致。
- `52-157-4`: 题干 `F:M` 与 IMPORTANT `F:L` 冲突，agent 按一处约束执行但 golden 口径不同。
- `233-13284`: prompt 对空 End/Start 的区间语义与 golden 接受口径存在差异。

## 建议

1. 强化 prompt/skill 对“完整范围发现”的要求：凡是公式、汇总、筛选、排序、查找类任务，必须 inspect 或脚本读取完整 used range，不能只依赖 `spreadsheet_content` 示例行。
2. 对公式类任务增加硬性验证：若题面出现 formula、using formula、corrected formula、自动计算等词，必须验证目标区 `f` 公式文本，不允许只写静态值。
3. 对导出后验证设为默认步骤：至少用 openpyxl 或受控 CLI 回读 `output.xlsx` 的 answer_position，捕获导出兼容、结构缩小、样式丢失和公式缓存差异。
4. 在 skill 中补充 `univer export` 参数示例和错误恢复说明，减少 `--overwrite` 这类参数误用。
5. 对超时任务限制 API 探测和重复验证：先完成最小正确编辑和导出，再做有限抽样验证；避免在 300 秒窗口内反复探测样式、公式和导出。
6. 对 answer_position 与结构性删除/插入冲突的题目，在 runner/prompt 中明确优先级：结构移动是否允许影响 answer_position 外的行列。

## 证据

- 逐题报告: `ai-analyze/codex-gpt-5-5-verified400-all-20260525-153934/*.md`, `ai-analyze/codex-gpt-5-5-verified400-all-20260525-223740/*.md`
- run summary: `.runs/univer-agent/codex-gpt-5-5-verified400-all-20260525-153934/summary.json`, `.runs/univer-agent/codex-gpt-5-5-verified400-all-20260525-223740/summary.json`
- report: `report/codex-gpt-5-5-verified400-all-20260525-153934.json`, `report/codex-gpt-5-5-verified400-all-20260525-223740.json`
- eval: `outputs/eval_univer_agent_gpt-5.5_codex-gpt-5-5-verified400-all-20260525-153934.json`, `outputs/eval_univer_agent_gpt-5.5_codex-gpt-5-5-verified400-all-20260525-223740.json`
