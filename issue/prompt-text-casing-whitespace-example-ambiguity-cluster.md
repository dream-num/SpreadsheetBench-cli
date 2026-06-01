# 文本大小写、空格保真与示例优先级失败簇

## 背景

本 issue 合并以下来源的重点：

- `issue/prompt-label-normalization-trim-context.md`：label/reference text、大小写、尾随空格保真相关实验记录。
- `issue/evaluation-dataset-quality-bugs.md` 中 `486-17` 的异常数据 / golden 机械截取结论。
- 11 题高并发回归 run：
  `tmp-codex-gpt-5-5-verified400-string-label-risk-v3-plus53383-20260601-161610`

本簇关注同一类风险：题面 literal、workbook 中可见/存储文本、已有示例、公式自然结果和 golden 口径之间不一致时，agent 需要做取舍。设计 prompt 或策略时不能知道 golden，只能基于题目、workbook 状态、answer_position、工具输出和通用 spreadsheet 语义推导。

## 当前复核口径

正式评测使用 `openpyxl.load_workbook(..., data_only=True)`，只比较 `answer_position` 内的 `cell.value`，并对数字做两位 round，对空字符串和 `None` 视为相等。

`plus53383` 运行结束时报告为：

| 项 | 数量 |
| --- | ---: |
| Docker task ok | 11 |
| PASS | 5 |
| FAIL | 6 |
| TIMEOUT/ERROR | 0 |

报告中的 FAIL：

`170-13`, `486-17`, `50486`, `51680`, `53383`, `56953`

随后直接复查当前 `outputs/univer_agent_gpt-5.5` 下的 xlsx，结果为 `8 PASS / 3 FAIL`，仍 FAIL：

`486-17`, `50486`, `53383`

注意：`170-13`, `51680`, `56953` 的 output 文件 mtime 晚于 `plus53383` eval/report 时间，当前共享 output 目录已不能代表该 run 评测瞬间的文件状态。后续分析这三题时应优先使用对应 run 的 agent 日志、eval JSON 与隔离重跑结果，而不是复用共享 output 路径。

## 逐题结论

### 486-17: 异常表头行 vs 宏式机械截取

题目描述：

把形如 `0yyyymmdd` 的日期数字从 `B2` 开始改成 `yyyy mm dd`，无表头。检查范围是 `'Blad1'!B2:B130`。

agent 抉择：

日志中 agent 先按 `A2:A130 -> B2:B130` 逐行转换；验证时发现 `A99:A101` 是重复表头文本 `Datum verzending`，不是 `0yyyymmdd` 日期码，于是更新计划，将对应 `B99:B101` 留空。这个选择符合“numbers that represent dates”和“no header”的题面语义。

评测差异：

golden 对 `A99:A101 = "Datum verzending"` 也机械套用了固定字符截取，相当于：

```text
Mid(value, 2, 4) & " " & Mid(value, 6, 2) & " " & Mid(value, 8, 2)
```

因此期望：

```text
B99:B101 = "atum  v er"
```

当前 output/golden 差异：

```text
Blad1!B99   output=None   golden="atum  v er"
Blad1!B100  output=None   golden="atum  v er"
Blad1!B101  output=None   golden="atum  v er"
```

归因：

题目异常数据 / golden 机械口径与题意冲突。agent 选择留空是合理语义处理，不应归为 `univer-cli` 错误。若为了评测通过，可提示 macro/公式式固定字符转换在 answer_position 覆盖整段时考虑“机械套用到异常文本”的反证，但该方向有过拟合风险，会鼓励生成无意义字符串。

### 50486: instruction literal title case vs workbook/header uppercase

题目描述：

根据两列中哪列有数字，在 `A2:A5` 显示文本 `Chep` 或 `Loscam`。workbook header 是 `C1="CHEP"`、`D1="LOSCAM"`。

agent 抉择：

agent 明确把题目里的 `'Chep'` / `'Loscam'` 当作要写入的 literal display text。它也检查到了源 header 为 uppercase，但在 Decision review 中认为“user explicitly requested text `Chep` or `Loscam`”，所以把整个 `A2:A5` 写成 title case：

```text
Chep, Chep, Loscam, Loscam
```

评测差异：

golden 采用 workbook/header 的 uppercase：

```text
Sheet1!A2  output="Chep"    golden="CHEP"
Sheet1!A3  output="Chep"    golden="CHEP"
Sheet1!A4  output="Loscam"  golden="LOSCAM"
Sheet1!A5  output="Loscam"  golden="LOSCAM"
```

归因：

题面 literal 与 workbook/header casing 冲突。按用户文字，agent 输出 title case 是合理的；按评测，应该复用 header casing。这个 case 不能简单作为“workbook label 永远覆盖题面 literal”的 prompt 证据，否则会误伤明确要求写入 literal text 的题。

候选策略：

当题面 literal 与源 header 只差大小写，且输出类别实际由 header 列决定时，agent 应显式记录冲突，并在验证中同时列出“literal 输出”和“header label 输出”的证据。是否选择 header casing 需要更窄规则约束，不能全局化。

### 53383: lowercase literal vs 示例/评测 title case

题目描述：

在 `worksheet2!C3:C6` 写公式，按 name/status 与另一个 worksheet 匹配，返回 `matched` 或 `not matched`。

agent 抉择：

agent 在 Task brief 和 Decision plan 中把题面文字解析为 lowercase literal：

```text
return literal text "matched" when both align, otherwise "not matched"
```

并写入公式：

```text
IFERROR(IF(VLOOKUP(...)=Brow,"matched","not matched"),"not matched")
```

评测差异：

golden 期望 title case：

```text
worksheet2!C3  output="matched"      golden="Matched"
worksheet2!C4  output="not matched"  golden="Not Matched"
worksheet2!C5  output="matched"      golden="Matched"
worksheet2!C6  output="matched"      golden="Matched"
```

归因：

大小写口径冲突。题面提供 lowercase literal，而 workbook 示例 / golden 采用 title case。agent 的逻辑匹配正确，失败只来自输出 label casing。该题可和 `50486` 一起用于验证“literal vs workbook/example casing”的不稳定性，但不应作为无条件保留 source/header text 的证据。

候选策略：

当题面要求写固定文字，但目标区域已有示例输出或表头显示风格时，应把大小写作为 output-affecting 决策单独 review：题面 literal、现有目标示例、header/display convention 三者谁优先。验证必须用 exact stored value，而不能只看语义。

### 51680: header trailing space preservation仍不稳定

题目描述：

按 `A:F` 每行的 `Y/N`，把对应 `A1:F1` header 文本按顺序用 comma join 写到 `G2:G14`，无尾随 comma。

关键 workbook 事实：

`C1` 存储值是 `"Green "`，包含尾随空格。golden 期望 join 后保留该空格，例如：

```text
Blue, Green , Orange, Brown
```

agent 抉择：

在 `plus53383` 日志中，agent 检查到了 `C1="Green "`，但被既有目标示例带偏，写下规则：

```text
use the inspected display label with trailing delimiter whitespace removed
```

也就是输出 `Green`，不是 `Green `。这与新增的“复制/join header 文本应保留 inspected source text”原则相冲突。

评测情况：

`plus53383` eval JSON 标记 `51680` FAIL。由于共享 output 文件之后被覆盖，当前 xlsx 复查已经 PASS，不能再用当前 output 复现该 run 的 FAIL 值；但日志足以说明该次 agent 决策仍存在 trim header 的不稳定性。

归因：

agent 自身决策不稳定：有时遵守 source-label preservation，有时被 partial existing examples 覆盖。该题是本簇里最重要的 prompt 稳定性回归样本之一。

候选策略：

对“include/copy text from headers/source cells”类任务，partial target examples 只能指导 separator/layout，不能授权 trim source header。Decision review 应把“existing examples conflict with exact source label”作为冲突项，而不是直接把 examples 作为 trim 证据。

### 56953: 数值行过滤 vs 示例连续块包含二级表头

题目描述：

根据 `F2` 的 Power 值，在 `I2:L13` 输出两个预定义范围中匹配的数据；题面同时说 row 2 是 column headers，下面是 numerical values，且 70 kW 的 desired result 在 orange range 中展示。

agent 抉择：

agent 选择语义上较干净的表格输出：

- `I2:L2` 放 `A2:D2` header；
- `I3:L8` 放 `Power=70` 的六个 numeric rows；
- `I9:L13` 空白；
- 排除 `A7:D7` 的 `Engine HS` 二级表头，因为题面说 numerical values underneath。

历史评测差异：

golden 更接近“复制 orange example 的连续块”：在 `I7:L7` 位置包含二级表头：

```text
Power (kW), Engine HS, Power take-off (rpm), (Nm)
```

随后 `I8:L9` 是 HS 两行数据。agent 排除二级表头后，后续行整体上移或为空。

`plus53383` eval JSON 标记 `56953` FAIL；但当前共享 output 文件之后被覆盖，当前 xlsx 复查已 PASS，不能再用当前 output 代表该 run 的评测瞬间。

归因：

题面语义与 workbook 示例优先级冲突。若按“numerical values underneath”，agent 排除二级表头合理；若按橙色 desired result/example，应该保留连续块中的二级表头。该题不适合简单评价 label/trim prompt；它更适合作为“示例区域是否是强答案模式”的策略样本。

### 170-13: 高并发 run 报告 FAIL，但当前 output 复查无值差异

题目描述：

用 `Sheet2` headers 匹配 `Sheet1` Entry 列，将匹配的 `Sheet1` entry 与 `Sheet2` 关联数据拼接到 `Sheet3!A:A` 的 `Output` 下；未匹配 header 忽略。

agent 抉择：

agent 检查到 `Sheet3` 只有前两组 header 的 partial output，于是按 `Sheet2` header 从左到右、`Sheet1` 匹配行顺序、每个 associated data 值逐条拼接，生成完整 `Sheet3!A1:A77`。它还验证了 VisualPerformance 和 LayerStructure 两组新增输出。

评测情况：

`plus53383` eval JSON 标记 `170-13` FAIL；但当前共享 output 文件 mtime 晚于该 eval/report 时间，且复查 `Sheet1!A1:A50`, `Sheet2!A1:E20`, `Sheet3!A1:A50` 与 golden 的 `data_only=True` 值差异为 0。

归因：

当前证据不足以把 `170-13` 归因给 prompt 或 agent。它应暂记为高并发 run 报告/共享 output 可复现性异常或需要隔离重跑的样本。若后续隔离 run 仍 FAIL，再按日志和当次 output 重新定位。

## 横向模式

1. **Literal vs workbook/example display text**
   - `50486`: `Chep/Loscam` vs `CHEP/LOSCAM`
   - `53383`: `matched/not matched` vs `Matched/Not Matched`

2. **Source text保真 vs partial target example**
   - `51680`: source header `Green ` 应保留，但 agent 有时根据已有 G 列示例 trim。

3. **题面语义 vs golden/example 连续块**
   - `56953`: numerical rows 语义支持排除二级表头；orange example/golden 支持保留二级表头。

4. **语义清洗 vs macro机械执行**
   - `486-17`: 留空异常 header 合理，但 golden 机械截取异常文本。

5. **高并发报告稳定性 / 共享 output 风险**
   - `170-13`, `51680`, `56953` 在本次报告和当前 xlsx 复查之间存在不一致；后续做稳定性判断时应优先隔离 run，并避免依赖可能被后续任务覆盖的共享 output 路径。

## 建议

- 不要把 `50486`、`53383` 简单修成“所有 literal 都按 workbook casing 输出”。更稳妥的通用提示是：当 fixed output text 与 workbook/example casing 冲突时，必须把大小写作为单独决策 review，列出题面 literal、已有目标示例、源 header 三方证据。
- 对 `51680` 这类 “include/copy text from headers” 任务，应继续强化 source-label exactness：partial target examples 可指导 separator，但不能授权 trim header 原文。
- 对 `56953` 这类目标区域已有示例输出的公式修复题，需要引导 agent 判断示例是否是 desired result block，而不仅是布局提示；如果示例是题面明确的 desired result，应优先复刻其结构，包括中间 section header。
- 对 `486-17` 不建议作为 prompt 通用修复目标，除非明确接受“宏式固定字符任务机械处理异常文本”的评测导向。
- 对高并发波动题，稳定性实验应使用 run 内 task workspace 的 output 或隔离输出目录；共享 `outputs/univer_agent_gpt-5.5/1_<task>_output.xlsx` 后续可能被覆盖，不适合长期留作证据。
