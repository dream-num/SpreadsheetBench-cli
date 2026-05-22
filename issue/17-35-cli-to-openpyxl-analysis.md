# 17-35: 从 univer CLI 链路转向 openpyxl/ExcelJS 的过程分析

## 背景

- run-id: `codex-gpt-5-5-verified400-first80-20260522-033617`
- task-id: `17-35`
- instruction_type: `Sheet-Level Manipulation`
- 工作表: `FILTER 5b`
- answer_position: `I6:M295`
- 最终状态: `ok`
- 评测结果: `test_case_results: [1]`
- 用时: `150.349s`

题目要求根据 `I2:J2` 的起止日期筛选 `A1:E315`，从 `I6` 开始输出筛选结果，并保持被带入行的原始格式。

最终结果是正确的：输出共 289 行，填充到 `I6:M294`，`I295:M295` 为空。

本 issue 关注的问题不是最终答案，而是 agent 为什么没有优先使用已有 `.univer` 编辑链路，而是转向了 `.xlsx + openpyxl/ExcelJS`。

## 任务 prompt 中的相关上下文

prompt 明确给出了 `.univer` 作为预导入 workbook:

```text
/task/cases/case_1/input.univer: pre-imported workbook for case 1.
```

同时也给出了规则：

```text
The `.xlsx` inputs have already been imported to `.univer`; you can use the `.univer` files directly.
The original `.xlsx` files are still available as source references, but you normally do not need to import them yourself.
Create the required `output.xlsx` for every case. These files are the final deliverables.
Solve every case independently and only modify cells within `answer_position`.
```

这里的本意是优先使用 `.univer`，`.xlsx` 只作为 source reference。但对于这题，“maintain the original formatting” 触发了 agent 对格式保真的额外担忧。

## Skill 文档中的相关上下文

`univer-cli` skill 的主线是把 `.univer` / `.unv` 当作 CLI 操作目标：

```text
`.univer` and `.unv` files are CLI operation targets, not agent-editable data stores.
Read and write workbook data through public CLI surfaces such as `inspect`, `search`, `pipe`, `run`, `export`, `status`, and `commit`.
```

命令选择表也指向：

```text
Hand back Excel-compatible output -> univer export
Write a known rectangular matrix back -> univer pipe in
Apply bounded workbook-local logic -> univer run --file
```

所以 skill 没有直接建议绕过 `.univer` 去编辑 `.xlsx`。相反，它倾向于 `.univer -> run/pipe -> inspect -> export`。

不过 skill 描述里也出现了：

```text
Excel-compatible `.xlsx` handoff
formatting
layout
```

这些词本身没有误导，但与题目中的“maintain original formatting”叠加后，可能让模型把“高保真 Excel 格式”联想到 openpyxl/ExcelJS。

## Agent 实际执行过程

### 1. 初始路径是准备使用 univer CLI

agent 先加载 skill，然后执行：

```text
univer help run
univer inspect range /task/cases/case_1/input.univer --range 'FILTER 5b'!A1:M20
univer inspect workbook /task/cases/case_1/input.univer
```

它识别到 workbook 只有一个工作表 `FILTER 5b`，并发现公式条件区域 `M2:N2`。

此时 agent 的计划仍然是 `.univer` workbook script：

```text
The workbook has one sheet, `FILTER 5b`, with formulas already forming criteria cells `M2:N2`.
I’m going to use a workbook script so I can copy both values and row formatting from `A:E` into `I:M`,
while keeping the edit bounded to `I6:M295`.
```

这说明 agent 起初没有放弃 CLI，而是准备通过 `univer run` 在 `.univer` 内完成。

### 2. Agent 查询 run formatting/ranges 帮助

随后它执行：

```text
univer help run formatting
univer pipe out /task/cases/case_1/input.univer --range 'FILTER 5b'!I2:J2 --format json --type rawValue
univer help run ranges
```

`run ranges` 帮助中有：

```text
getValues()
getRawValues()
setValues()
clear()
clearContent()
clearFormat()
autoFill()
```

`run formatting` 帮助中有：

```text
setFontWeight()
setFontLine()
setFontFamily()
setFontSize()
setFontColor()
setFontStyle()
setBackgroundColor()
setHorizontalAlignment()
setVerticalAlignment()
setBorder()
setNumberFormats()
clearFormat()
```

这些 API 可以支持值、数字格式、部分视觉格式写入，但没有展示一个直接的“复制源单元格完整格式到目标单元格”的范式，例如：

- `copyTo`
- `copyFormatFrom`
- `getStyle` / `setStyle`
- 复制完整 cell style 对象
- 复制 row height
- 复制源行 `A:E` 到目标行 `I:M` 并保留所有 Excel 样式

这很可能是转折点。

### 3. Agent 改口转向原始 xlsx

查询帮助后，agent 做出了新的判断：

```text
The criteria are `2023-03-22` through `2024-04-23`.
I’m going to generate the final `.xlsx` from the original `.xlsx` reference
so the copied result rows can carry Excel cell styles, number formats, fills, borders, and row heights accurately.
```

这个理由不是来自工具报错，也不是来自明确的 CLI 限制，而是 agent 根据以下因素自行推断：

- 题目明确要求保持原始格式。
- `univer help run formatting` 没有提供完整样式复制 API。
- 原始 `.xlsx` 文件存在。
- openpyxl/ExcelJS 是模型熟悉的 Excel 格式复制工具。

### 4. openpyxl 路径失败

agent 复制了原始 xlsx：

```text
cp /task/cases/case_1/input.xlsx /task/work/case_1_work.xlsx
```

然后生成 openpyxl 脚本并尝试运行：

```text
python /task/work/filter_case_1.py
```

失败：

```text
/bin/sh: python: not found
```

再尝试：

```text
python3 /task/work/filter_case_1.py
```

失败：

```text
/bin/sh: python3: not found
```

这说明转向 openpyxl 不是一个稳定路径，因为容器环境里并没有 Python。

### 5. 改用 ExcelJS，并运行时安装依赖

随后 agent 检查 Node/npm，发现可以使用：

```text
which node
which npm
```

但本地没有 `exceljs`，于是运行：

```text
npm init -y >/dev/null && npm install exceljs@4 >/dev/null
```

这引入了额外风险：

- 依赖网络和 npm registry。
- 增加运行耗时。
- 在沙箱、DNS、认证、registry 不稳定时可能失败。
- 与 benchmark 中希望稳定复现的执行链路相冲突。

### 6. ExcelJS 路径最终成功

最终脚本读取：

```js
const input = "/task/cases/case_1/input.xlsx";
const output = "/task/outputs/case_1/output.xlsx";
```

它执行的核心逻辑是：

- 读取 `I2:J2` 起止日期。
- 遍历 `A6:E315`。
- 日期在范围内的行复制到 `I:M`。
- 清空 `I6:M295` 未用区域。
- 复制 value、style、numFmt、note、hyperlink。
- 写出 output.xlsx。

运行成功：

```text
wrote /task/outputs/case_1/output.xlsx with 289 filtered rows
```

后续验证时曾出现一次 CLI 参数错误：

```text
univer import ... --overwrite
```

失败：

```text
Unknown argument: overwrite
```

agent 删除目标目录后去掉 `--overwrite` 重新 import，验证成功。

## 为什么没有优先使用已有 .univer 编辑链路

直接原因是 agent 判断 `.univer run` 的公开 API 不足以高保真复制完整 Excel 格式。

更具体地说：

1. 它原本准备使用 `univer run`。
2. 查询 `run formatting` / `run ranges` 后，没有看到完整格式复制范式。
3. 题目强调 `maintain the original formatting`。
4. prompt 又说明原始 `.xlsx` 仍可作为 source reference。
5. agent 因此选择了它熟悉的 openpyxl/ExcelJS 路径来复制 Excel 样式。

这不是 skill 明确误导的结果，而是 skill/API 文档缺口和模型保守推理共同导致的。

## Skill 和 univer 命令是否存在误导

### 没有直接误导

skill 明确建议：

- `.univer` 是 CLI 操作目标。
- 用 `inspect` / `pipe` / `run` / `export`。
- 不要编辑 `.univer` 内部文件。
- 用 `univer help` 查命令语法。

这些都没有鼓励 agent 直接编辑 `.xlsx`。

### 存在容易被模型放大的空白

`univer help run formatting` 展示的是设置格式 API，而不是复制格式 API。

对这题来说，用户不是要求“设置某个新格式”，而是要求“把原始行格式带过去”。agent 需要一个类似下面的明确 recipe：

```text
For filtered copy tasks that must preserve existing formatting,
prefer workbook-native APIs first. Use setValues for values,
setNumberFormats for number formats, clearContent for unused cells,
and verify export. Only fall back to input.xlsx if a concrete CLI/API limitation is observed.
```

如果没有这个 recipe，模型容易把“完整样式复制”理解为 Excel 文件层面的任务，从而绕到 openpyxl/ExcelJS。

## 问题归类

这是“最终正确但过程有问题”的 case。

问题类型：

- 工具链路径选择不稳。
- 对 `.univer` 格式能力缺乏信心。
- 运行时依赖安装。
- 环境假设错误。
- CLI 参数猜测。

不是以下类型：

- 不是题意理解错误。
- 不是 answer_position 越界。
- 不是 `setValue(null)` / `setValues(null)` 失败。
- 不是 `.univer` 本身运行失败导致的 fallback。

## 改进建议

### Prompt 改进

建议加入：

```text
When formatting must be preserved, first attempt the existing .univer workflow with univer run / pipe / export.
Do not switch to editing input.xlsx with external libraries only because formatting is mentioned.
Use input.xlsx only as a read-only reference or as a fallback after a concrete univer CLI/API limitation is observed.
Do not install npm packages at runtime for workbook editing unless explicitly necessary.
Before concluding formatting cannot be handled in univer, check the relevant run help topics, including formatting, ranges, and sheets.
```

### Skill 文档改进

建议给 `univer-cli` skill 增加一个“筛选复制并保留格式”的 recipe，明确优先级：

1. 优先 `.univer + run/pipe + export`。
2. 简单值复制用 `setValues()`。
3. 清空未用输出区域用 `clearContent()`，避免破坏已有格式。
4. 数字格式需要保留时用 `setNumberFormats()`。
5. 如果需要完整 cell style、row height、fill、border 的一比一复制，而当前 CLI API 没有稳定公开方式，必须在报告中说明具体 CLI/API 缺口，再 fallback 到 `.xlsx`。

### Agent 行为约束

建议在 runner prompt 中增加：

- 不要因为“formatting”字样直接选择 openpyxl/ExcelJS。
- 运行脚本前先确认解释器存在。
- 禁止默认 `npm install`。
- 使用 CLI 参数前必须查 `univer help <command>`。

## 结论

这题的转向不是因为 `.univer` 编辑链路实际失败，而是因为 agent 在看到格式保留需求后，对 `.univer run` 的格式复制能力缺乏信心。

skill 没有直接误导，但 `run formatting/ranges` 文档缺少“复制已有格式”的强范式，prompt 又允许 `.xlsx` 作为 source reference，最终让 agent 选择了更熟悉但更脆弱的 `.xlsx + openpyxl/ExcelJS` 路径。
