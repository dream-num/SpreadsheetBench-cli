# 55427 公式修复任务中返回列选择不稳定

## 背景

- task id: `55427`
- dataset: `spreadsheetbench_verified_400`
- agent/model: `codex` / `gpt-5.5`
- answer_position: `Compiled and located schools da'!B2:B1461`
- 相关 sheet:
  - `Compiled and located schools da`
  - `URN lookup`
  - `KS4 data`

题目要求修复 `Compiled and located schools da` 中 `DFES check` 列的 `INDEX/MATCH` 公式。原始公式示例：

```excel
=INDEX('URN lookup'!$D$2:$D$1461,MATCH(L2,'URN lookup'!$K$2:$K$1461,0))
```

实际失败原因之一是 `Compiled and located schools da!L:L` 中邮编带前导空格，而 `URN lookup!K:K` 不带前导空格，因此应使用 `TRIM(Lrow)` 参与匹配。golden 在真实数据行 `B2:B1419` 中保留返回范围 `URN lookup!D:D`，只把匹配键改为 `TRIM(Lrow)`；`B1420:B1461` 为空。

## 已观察到的失败形态

### 1. 边界污染

历史 run 中 agent 按 `answer_position` 末行理解为必须填满 `B2:B1461`，扩展工作表并在 `B1420:B1461` 写入公式，导致这些空白尾部行计算为 `#N/A`，评测失败。

代表 run:

- `codex-gpt-5-5-high-verified400-wrong86-w8-20260526-150018`

证据：

- output 相对 golden 在 `B1420:B1461` 多出公式和值 `#N/A`。
- 日志中多次出现 `Range is out of bounds`，随后 agent 用 `sheet.setRowCount(1461)` 扩展行数。

### 2. 返回列不稳定

临时提示词实验强调 `answer_position` 是最大允许边界后，边界污染有所改善；但 agent 仍有概率把返回列从原公式的 `URN lookup!D:D` 改为 `URN lookup!E:E`。

失败 run:

- `tmp-codex-gpt-5-5-verified400-task55427-answer-position-boundary-prompt-rerun2-20260526-174936`

该 run 的行为：

- 正确只写 `B2:B1419`，`B1420:B1461` 保持空白。
- 错误将公式改为：

```excel
=INDEX('URN lookup'!$E$2:$E$1461,MATCH(TRIM(L2),'URN lookup'!$K$2:$K$1461,0))
```

导致大量值从 golden 期望的 `ESTAB` 变成 `LAESTAB`：

- output `B2 = 9092002`
- golden `B2 = 2002`
- `openpyxl(data_only=True)` 对 `B2:B1461` 检出 `1312` 个差异。

通过 run:

- `tmp-codex-gpt-5-5-verified400-task55427-answer-position-boundary-prompt-rerun1-20260526-174414`
- `tmp-codex-gpt-5-5-verified400-task55427-answer-position-boundary-prompt-rerun3-20260526-174937`

这些 run 均保留 `URN lookup!D:D`，只加入 `TRIM(Lrow)`，并通过评测。

## 当前判断

边界提示词方向对“不要污染空白尾部行”有效，但不应单独提交为已验证修复，因为该 task 仍暴露出另一个 agent 推理不稳定点：修复已有公式时，agent 可能过度解释题意，把原公式的返回字段从 `ESTAB` 改成 `LAESTAB`。

这不是 `univer-cli` 写入或导出问题。相关 run 中 workbook 写入、导出和评测读取都正常；失败来自 agent 对业务字段的选择不稳定。

## 候选改进

后续若继续改 prompt，可考虑加入通用规则：

```text
When repairing an existing formula, preserve the original formula's output range, return column, and result field unless the instruction explicitly requires changing them or workbook evidence proves the original return field is wrong. Prefer the smallest formula change that fixes the observed failure condition.
```

该规则需要和边界规则一起重新做单变量实验；不要把本 issue 的临时提示词实验结果直接当作已验证修复提交。

## 本地验证记录

- 本地 runner 测试曾验证 prompt 文本可生成，但该改动已按要求撤回。
- 单题实验结果：
  - `rerun1`: PASS
  - `rerun2`: FAIL，返回列 D 被改为 E
  - `rerun3`: PASS
- 当前不保留 prompt/test 改动，只记录 issue 和矩阵备注。
