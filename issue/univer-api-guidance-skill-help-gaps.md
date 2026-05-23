# Univer API help/skill 文档缺口导致 agent 误用、探测或超时

## 背景

- dataset: `spreadsheetbench_verified_400`
- 主要关联 run-id:
  - baseline: `tmp-claude-deepseek-v4-flash-verified400-first40-wrong-rerun2-w10-20260523-191445`
  - prompt 实验: `claude-api-guidance-related-20260523-200359`
- 关联 task-id:
  - `120-24`: 扩列到远端列、背景色写入
  - `423-16`: 写入宽 range / 扩列后再操作
  - `177-6`: raw values、数字字符串、NBSP 空白
  - `73-45`: rich text / 局部高亮
  - `61-4`: 严格保留文本空白和输出逻辑验证

在分析 Verified 400 错题时发现，多类失败不是单纯题意理解问题，而是 agent 对 Univer facade API、`univer help run` 和 `univer-cli` skill 中未充分说明的行为做了猜测或反复探测。后续通过在 benchmark prompt 中补充通用 API 注意事项，部分 case 明显改善，但这些知识更适合沉淀到 `univer-cli` skill 或 `univer help run` 文档中，而不是长期依赖 benchmark prompt。

## 问题

### 1. 越界 range 创建时机不清楚

`FRange` 在创建时会立即按当前 sheet 的 `rowCount` / `columnCount` 校验边界。目标 range 超出当前边界时，`getRange()` 会直接抛错：

```text
Range is out of bounds. Max rows: ..., Max columns: ...
```

在 `120-24` 和 `423-16` 中，agent 尝试直接创建远端列或宽 range，导致写入前就失败。它虽然能推断“可能需要扩列”，但不清楚必须先扩展 sheet 边界，再重新创建 range。

影响：

- 远端列写入任务无 output。
- agent 在 `insertColumns`、`setValues`、重复 restore/export 之间试探，浪费时间。
- 容易把“扩大可写边界”和“插入列并移动已有数据”混为一谈。

### 2. 扩列 API 语义不够明确

对于“只是让右侧远端列可写”的任务，`setColumnCount(requiredColumnCount)` 更直接；对于“在中间插入列并移动已有数据”的任务，才应该使用 `insertColumns()` / `insertColumnsBefore()` / `insertColumnsAfter()`。

目前 help/skill 中没有把这两个意图区分得足够明确，agent 容易为了写远端列去尝试插列，带来列位移风险。

### 3. 背景色读写与样式内部结构关系不清楚

背景色有 facade API：

```javascript
range.setBackgroundColor(color)
range.setBackground(color)
range.getBackground()
range.getBackgrounds()
```

但 agent 常尝试读取或构造 `cellData.s`，并用内部 style id / composed style 推断背景色是否成功。这会引入不稳定判断，也会把“cell style 内部表示”和“facade 可验证状态”混淆。

在 `120-24` 中，背景色和远端列写入同时出现；明确使用 facade 背景色 API 后，该 case 在小范围实验中通过。

### 4. Rich text / 局部高亮 API 不够可发现

Rich text 有正式 builder 和 range API：

```javascript
const richText = univerAPI
  .newRichText()
  .insertText(text)
  .setStyle(start, end, style);

range.setRichTextValueForCell(richText);
range.setRichTextValues(values);
```

但 agent 容易猜测 `cell.p.body.textRuns` 内部结构，或反复探测局部样式是否能 export 到 xlsx。在 `73-45` 中，补充提示后 agent 已经改用 `newRichText().insertText().setStyle()` 和 `setRichTextValueForCell()`，并成功导出 output，但它在导出后继续做额外 final check，遇到模型 429 重试，最终 runner timeout。

这说明 rich text API 指引有效，但仍需要在 skill/help 中更明确地说明：

- 首选 builder API，不要手写内部 `p` 结构。
- 如何读取/验证 rich text。
- export 前后哪些验证足够，避免无意义探测。

### 5. `getRawValues()` 的“raw”语义容易被误解

`getRawValues()` 返回存储值本身：

- rich text 返回 `cell.p.body.dataStream`
- 普通单元格返回 `cell.v`

它不会：

- 清洗 NBSP (`\u00A0`)
- trim 普通空白
- 去掉千分位逗号
- 把 numeric-looking string 自动转成 number

在 `177-6` 中，agent 需要处理数字字符串、NBSP 空白和分组求和。没有明确指引时，它容易卡在 raw/display 值语义和空白判断上；补充 normalize 规则后，该 case 在小范围实验中通过。

### 6. 读取 normalize 与写回保真边界不清楚

normalize 适合内部比较、判空、求和、排序、筛选，但不应盲目用于写回。部分任务要求保留原始文本、尾随空格或格式。`61-4` 的失败显示，agent 即使能处理空白，也可能因为业务逻辑和保真验证不足造成错位或值差异。

因此文档中需要同时说明：

- 内部逻辑可以 normalize。
- 输出写回时要按题目要求保真。
- 对尾随空格、原始字符串、日期/数字格式敏感任务，必须验证 output 与 golden 口径相关的值类型、格式和空白。

## 已验证的临时 prompt 改进

在 `inference/univer_agent/prompts.py` 中临时补充了通用规则：

- 越界写入前先扩展 sheet 边界，再创建 range。
- 简单扩展可写列数使用 `setColumnCount(requiredColumnCount)`；只有需要移动已有数据时才用 `insertColumns*`。
- 背景色使用 `setBackgroundColor` / `getBackgrounds`。
- rich text 使用 `newRichText().insertText().setStyle()` 和 `setRichTextValueForCell` / `setRichTextValues`。
- `getRawValues()` 不做清洗或类型转换，比较/求和前显式 normalize。
- normalize 只用于内部逻辑，不要盲目 trim 写回值。

小范围实验：

```text
run-id: claude-api-guidance-related-20260523-200359
tasks: 73-45, 120-24, 177-6, 423-16, 61-4
result: 3/5 correct
correct: 120-24, 177-6, 423-16
failed: 61-4
timeout: 73-45
```

效果：

- `120-24` 从 BN/远端列越界无 output 变成正确。
- `423-16` 从宽 range 越界无 output 变成正确。
- `177-6` 从 timeout 变成正确。
- `73-45` rich text 写法已改对并导出 output，但导出后额外验证遇到 429，最终 timeout。
- `61-4` 仍是 agent 业务逻辑和验证问题，不是 API 文档可直接解决。

## 后续 skill/help 需要加强

### `univer help run ranges` / `univer help run sheets`

建议补充：

- `getRange()` 创建时会立即边界校验。
- 写入超出当前 sheet 边界的行/列时，必须先扩展边界，再重新创建 range。
- `setColumnCount()` / `setRowCount()` 用于扩大可写边界。
- `insertColumns*` / `insertRows*` 用于插入并移动已有数据，不应作为远端列写入的默认手段。

### `univer help run formatting`

建议补充：

- 背景色首选 `setBackgroundColor()` / `setBackground()`。
- 验证背景色首选 `getBackground()` / `getBackgrounds()`。
- 不建议 agent 通过 `cellData.s` 或内部 style id 判断背景色是否成功，除非是在诊断导入/导出问题。

### `univer help run rich-text` 或 formatting 文档中的 rich text 小节

建议补充：

- `univerAPI.newRichText()` / `newRichTextValue()`。
- `.insertText()`、`.setStyle(start, end, style)`。
- `setRichTextValueForCell()` / `setRichTextValues()`。
- `getValue(true)` / `getValues(true)` 的读取方式。
- 说明 `cell.p.body.textRuns` 是内部模型，不应作为 agent 首选写入路径。
- 给一个局部红色加粗高亮的最小示例。

### `univer help run values` / `univer-cli` skill 的值读取章节

建议补充：

- `getRawValue()` / `getRawValues()` 不做文本清洗和类型转换。
- NBSP、普通空格、空字符串、`null` 的判空示例。
- numeric-looking string、带逗号数字字符串的 parse 示例。
- normalize 只应用于内部逻辑，写回时要按题目保留原始文本、尾随空格或格式。

### `univer-cli` skill 的执行策略

建议补充：

- 对大范围、rich text、样式密集任务，完成一次 answer_position 相关验证并成功 export 后应停止。
- 不要在 export 后做无边界的 final check / re-import / 再验证循环。
- 遇到模型 429 或 agent API retry 时，额外验证会显著增加 timeout 风险。

## 风险

- 如果这些规则只存在于 benchmark prompt，会增加 token，并且其它使用 `univer-cli` 的 agent 场景仍会重复踩坑。
- 如果 help/skill 没有明确 API 选择边界，agent 会继续通过猜内部结构、探测 API 或重复导入导出来补知识缺口。
- 部分问题看似 agent 推理错误，但根因是文档没有把安全、稳定、可验证的 API 路径暴露给 agent。
