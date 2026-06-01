# 公式/VBA/lookup 任务中特殊值与填充边界决策不稳定

## 范围

- dataset: `spreadsheetbench_verified_400`
- agent/model: `codex` / `gpt-5.5`
- related tasks: `48983`, `55427`, `58949`, `5835`, `56915`, `524-31`
- 旧 issue 合并来源: `issue/55427-formula-repair-return-column-instability.md`

这组题共同暴露的问题是：VBA 转公式、公式修复、`INDEX/MATCH`、lookup/fill-down 任务中，agent 对特殊值、空源单元格、缺失匹配、尾部空白边界和已有公式返回字段的判断不稳定。当前 prompt 改动已经稳定修复 `48983`、`55427`、`58949`，但 `5835`、`56915`、`524-31` 仍失败或存在题目/golden 口径冲突。

## 相关运行

基线 run:

- `tmp-codex-gpt-5-5-verified400-formula-special-values-6tasks-20260601-163000`
- result: `PASS 1 / FAIL 5 / TIMEOUT 0`
- PASS: `48983`
- FAIL: `524-31`, `5835`, `55427`, `56915`, `58949`

当前 prompt run:

- `tmp-codex-gpt-5-5-verified400-formula-special-values-v2-headings-rerun-6tasks-20260601-182000`
- result: `PASS 3 / FAIL 3 / TIMEOUT 0`
- PASS: `48983`, `55427`, `58949`
- FAIL: `524-31`, `5835`, `56915`

稳定性:

- `tmp-codex-gpt-5-5-verified400-formula-special-values-v2-6tasks-20260601-173000`
- `tmp-codex-gpt-5-5-verified400-formula-special-values-v2-rerun-6tasks-20260601-181000`
- `tmp-codex-gpt-5-5-verified400-formula-special-values-v2-headings-rerun-6tasks-20260601-182000`

三次 v2 结果一致：`48983`、`55427`、`58949` 均 PASS；`5835`、`56915`、`524-31` 均 FAIL。

## 任务分析

### 48983: INDEX/MATCH 空源单元格自然返回 0

- answer_position: `M6:S11`
- 题目描述: 用户要用 `INDEX/MATCH` 将源品牌/分类交叉表的数据复制到 `L:S` 中对应品牌和分类的位置。
- 基线/当前 agent 抉择: 使用裸 `INDEX/MATCH` 公式，按目标品牌匹配源 `B6:B19`，按目标分类匹配源 `C5:I5`。对源值为空的命中交叉项，不额外包 `IF` 转 blank，而是让公式自然返回 `0`。
- 评测: 当前 run 中 `M6:S11` 为 `0 / 42` 差异，PASS。
- 结论: 这是当前公式特殊值规则的正向样本。关键原则是“found empty source cell”和“missing key/header”必须区分；命中空源单元格时不要擅自把公式自然 `0` 改为空白。

### 55427: 公式修复时真实数据边界与返回列保持

- answer_position: `Compiled and located schools da'!B2:B1461`
- 题目描述: 用户现有公式 `=INDEX('URN lookup'!$D$2:$D$1461,MATCH(L2,'URN lookup'!$K$2:$K$1461,0))` 无法正确 lookup DFES number，需要修复 `INDEX/MATCH` 后继续合并学校数据。
- 已合并旧 issue 重点:
  - 原公式失败的主要原因是 `Compiled and located schools da!L:L` 邮编带前导空格，而 `URN lookup!K:K` 不带前导空格，因此应在匹配值上使用 `TRIM(Lrow)`。
  - 历史失败形态一：agent 按 `answer_position` 末行填满 `B2:B1461`，导致真实数据末尾后的 `B1420:B1461` 变成 `#N/A`，污染尾部空白。
  - 历史失败形态二：agent 有时把返回列从原公式 `URN lookup!D:D` 改为 `URN lookup!E:E`，导致大量 `ESTAB` vs `LAESTAB` 值错误。代表失败 run: `tmp-codex-gpt-5-5-verified400-task55427-answer-position-boundary-prompt-rerun2-20260526-174936`，当时 `B2` output 为 `9092002`，golden 为 `2002`，`B2:B1461` 有 `1312` 个差异。
- 基线 agent 抉择: 已使用 `TRIM(Lrow)` 和正确返回列 `URN lookup!D:D`，但填满 `B2:B1461`；日志明确 `B1420`、`B1461` 自然返回 `#N/A`。
- 基线评测: `B1420:B1461` 共 `42` 个 `#N/A` vs blank 差异，FAIL。
- 当前 agent 抉择: 保留原返回列 `URN lookup!D:D`，只把匹配值改为 `TRIM(Lrow)`；只写真实数据范围 `B2:B1419`，清空/保留 `B1420:B1461`。
- 当前评测: `B2:B1461` 为 `0 / 1460` 差异，PASS。
- 结论: 当前规则稳定修复本题。关键原则是修复已有公式时保持返回范围/返回字段不变，并用真实数据边界决定填充范围；`answer_position` 是评测区域，不等于必须全部写公式的区域。

### 58949: VBA 转公式时 `N/A` placeholder 与 empty string 冲突

- answer_position: `'Desired Result'!B2:I5`
- 题目描述: 用户要把数据库导出的多行 client/detail 数据重组成每个 client 一行、按预定义 headers 横向展开；题面同时说缺失处填 `N/A`，又补充 “The formula data output result may be an empty string.”
- 基线 agent 抉择: 将缺失 client/header 组合写成 literal text `N/A`，并确认 `F2 = N/A`。
- 基线评测: `20 / 32` 差异，典型差异为 `Desired Result!D2:I2` 等多个单元格 golden 为 blank，output 为 `'N/A'`，FAIL。
- 当前 agent 抉择: 将缺失 client/header 组合留为空字符串，理由是匹配 workbook existing desired-result convention，并遵守题面 “formula output may be an empty string”。
- 当前评测: `Desired Result!B2:I5` 为 `0 / 32` 差异，PASS。
- 结论: 当前规则稳定修复本题。关键原则是 VBA/macro-to-formula 任务中，如果 placeholder 文本和公式输出约定冲突，应在 `Decision review` 中显式裁决，并优先 workbook-visible desired result / 公式输出约定，而不是机械写入题面提到的 placeholder。

### 5835: lookup 结果空白 vs 0 仍未解决

- answer_position: `C3:C19`
- 题目描述: 用户要把 Basic Table 中 `LOG VALUE` 列添加到 requested table 的对应 items 的 `C` 列。
- 当前 agent 抉择: 将 requested table `A:B` 匹配 Basic Table `H:G`，返回 `I` 列 LOG VALUE。对匹配源 `I` 为空的行写 blank；对没有匹配 source row 的行也写 blank。日志样本：
  - `C6` blank，理由是 matching source `I6` blank。
  - `C7` blank，理由是 no matching basic-table row。
  - `C17` blank，理由是 matching source `I12` blank。
- 当前评测: `10 / 17` 差异，golden 在 `C6:C14` 和 `C17` 均为 `0`，output 为 blank，FAIL。
- 判断: 这是尚未解决的 agent/golden 口径冲突。agent 的 blank 选择有可解释证据，但评测 workbook 期望无值/无匹配转为 numeric `0`。如果要继续修，需要更窄地引导 lookup/fill 任务在目标示例、已有公式、或公式自然结果显示无值为 `0` 时不要清空；不能泛化成“所有缺失都写 0”。

### 56915: 结构行 blank vs 0 仍未解决

- answer_position: `'COVER'!B18:E23`
- 题目描述: 用户要求在 `COVER!B18:E23` 填入与 `COVER` 表 column header 和 row header 对应的 `DATA` 表数据，entity 由 `COVER!B12` 选择；同时要求四舍五入到两位，并将 C/E 列设置为负数括号格式。
- 当前 agent 抉择: 修复 `B18:E18` 和 `B21:E23` 的公式，处理 `DATA` 表 merged entity headers；将 `B19:E20` 视作 blank structural rows 并保留空白；对 C/E 列应用 decimal negative-parentheses number format。
- 当前评测: `8 / 24` 差异，`COVER!B19:E20` golden 为 `0`，output 为 blank，FAIL。
- 判断: 本题仍暴露出“看起来像结构/空白行的 answer_position 内部行，golden 可能要求公式自然 0”的问题。因为用户明确说 populate `B18:E23`，agent 将中间两行排除为结构行的抉择和评测不一致。继续修复时应要求 agent 对 answer_position 内部的 blank structural rows 做反证验证：若题面要求填满整个范围，且相邻公式或 golden-like workbook convention 暗示公式自然结果为 `0`，不要仅凭视觉空白排除内部行。
- 注意: 用户明确担心 raw/display/rounding 规则误伤，本轮 prompt 没有加入通用 raw-value/显示值规则；本题仍 FAIL 主要来自 blank vs `0`，不是评测中的四舍五入显示问题。

### 524-31: `#N/A` vs blank 的题目/golden 口径问题

- answer_position: `'Exp-DB'!E1:E53`
- 题目描述: 用户有 bank-speak 交易描述和缩短 vendor keys，希望自动分配交易类别，不想使用大型 nested IF 或 VLOOKUP/INDEX-MATCH，认为可用 VBA 实现。
- 当前 agent 抉择: 将 `E1:E53` 改为按 `A1:B37` mapping table 和 `D1:D53` transaction descriptions 做 substring search 的公式；无匹配项返回 `"#N/A"` 文本。日志样本：
  - `E2 = amazon`
  - `E37 = refund`
  - `E45 = #N/A`
  - `E53 = groceries`
- 当前评测: `7 / 53` 差异，`E7`, `E8`, `E28`, `E29`, `E30`, `E45`, `E46` golden 为 blank，output 为 `'#N/A'`，FAIL。
- 判断: 这题不适合作为主要 prompt 修复目标。矩阵备注中已有结论：golden XML 中存在 VLOOKUP 公式，实际重算应为 `#N/A` 错误，但缓存值为空；题面也未说明无匹配项应为空、错误值还是文本。agent 写 literal `"#N/A"` 不是理想 error 类型，但当前 FAIL 更大程度是题目/golden 口径不一致，而不是分类映射错误。

## 当前结论

已验证有效的 prompt 方向:

- 公式/lookup 任务中，区分 found empty source、missing key/header、literal placeholder。
- VBA 转公式任务中，对 `N/A` vs empty string 这类冲突做显式裁决。
- 修复已有公式时，保持原返回列/返回字段，按真实数据边界填公式，不把 `answer_position` 尾部空白全填满。

尚未解决的风险:

- `5835` 和 `56915` 表明，agent 仍会把“空源/无匹配/结构空白行”解释为 blank，而部分 golden 期望 numeric `0`。
- 不能简单加“缺失一律写 0”或“N/A 一律 blank”，否则会误伤 `58949`、`524-31` 或其它确实需要 literal/error placeholder 的任务。
- `524-31` 需要保留为题目/golden 口径问题，不应作为通用 prompt 规则的硬目标。

## 候选后续改进

可以考虑新增更窄的原则，但需要单独实验：

```text
For lookup/fill tasks inside the requested answer_position, do not treat visually blank rows or empty source cells as blank output by default. If the task asks to populate the whole checked range, inspect existing target examples, source formulas, and formula-natural results to decide whether blank-looking cases should remain blank or evaluate to numeric 0. Record this decision separately for found-empty source cells, missing matches, and internal structural rows.
```

这条仍有误伤风险，尤其是 `58949` 这类明确允许 formula output empty string 的任务；必须保持在公式/lookup/fill-down 子标题下，并要求基于 workbook evidence 裁决，而不是默认输出 `0`。
