# 结构变更任务中 `answer_position` 需按最终布局解释

## 问题

当前 prompt 过去强调“只修改 `answer_position`”，但对插入/删除行列、添加标题/分区行、移动表格、转置数据等结构变更任务不够明确。agent 容易把 `answer_position` 当作原始 workbook 中的固定坐标，而不是最终 workbook 状态中的评测/填写范围。

这会导致日期行、表头、源区域、目标区域在结构变化后出现整体偏移。

## 触发样例

- Dataset: `spreadsheetbench_verified_400`
- Task: `42216`
- Baseline run: `codex-gpt-5-5-verified400-all-20260525-223740`
- Baseline result: `test_case_results=[0]`

题目要求先为 Group A 增加 April 相关行，并把 Group A 的月-日矩阵转换为 Group B 的逐日行数据。`answer_position` 为 `B20:B339`。

baseline agent 按原始 workbook 中 `A20=1951-01-02` 推断 `B20` 对应 1951-01-02；golden 的最终布局中 `B20` 对应 1951-01-01。结果整体偏移一天。

## 根因

prompt 没有明确说明：

- 结构变更任务中，应先推理最终 workbook 布局，再解释 `answer_position`。
- `answer_position` 是最终状态下需要验证和填写的范围，不一定等于原始 workbook 的固定坐标语义。
- 如果题目显式要求结构变更，可以在必要时影响 `answer_position` 外的结构；但普通值写入仍应限制在 `answer_position` 内。
- reshape/结构变更任务需要验证源坐标、最终目标坐标和语义键的映射，而不是只验证目标范围有值。

## 已实施修复

已在 `inference/univer_agent/prompts.py` 添加通用 prompt 规则：

- 对插入/删除行列、添加 section/header row、移动表、转置或其它结构变化，先推理最终布局再解释 `answer_position`。
- 对结构变化或数据重塑任务，至少验证首个目标、中间目标、末尾目标三个映射点，并确认源坐标、最终目标坐标和日期/表头/分类等语义键。

验证记录见：

- `fix-logs/2026-05-26-structural-answer-position-prompt.md`

## 验证结果

- Experiment run: `tmp-codex-gpt-5-5-verified400-task42216-structural-answer-position-prompt-rerun1-20260526-162349`
- Result: `test_case_results=[1]`
- `openpyxl` 对比 `B20:B339`：值差异数 `0`

## 剩余风险

- 当前只做了 `42216` 单题验证，未跑全量数据集。
- 对 `answer_position` 标注本身错误或不完整的题目，仍需逐题判断是否属于数据/题目问题。
