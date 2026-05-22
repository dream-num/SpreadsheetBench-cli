# 17-35: 使用 getValues 回写导致日期/金额类型和格式退化

## 背景

- task-id: `17-35`
- run-id: `codex-gpt-5-5-verified400-first20-w10-20260522-163839`
- dataset: `spreadsheetbench_verified_400`
- agent: `codex`, model `gpt-5.5`
- instruction_type: `Sheet-Level Manipulation`
- answer_position: `I6:M295`
- 推理状态: `ok`
- 评测结果: `test_case_results: [0]`
- 耗时: `132.682s`

题目要求根据 `I2:J2` 的起止日期筛选 `A1:E315`，从 `I6` 开始输出筛选结果，并保持带入行的原始格式。

这次运行已经遵守了新的 univer-only 约束：没有直接读取或修改 `input.xlsx`，没有使用 `openpyxl`、`exceljs`、`npm install`，最终通过 `univer export` 生成输出。但是结果评测失败。

## 现象

agent 使用 `.univer` 链路完成：

```text
univer pipe out /task/cases/case_1/input.univer --range 'FILTER 5b'!I2:J2 --format json --type rawValue --output /task/work/criteria_raw.json
univer pipe out /task/cases/case_1/input.univer --range 'FILTER 5b'!A5:E315 --format json --type rawValue --output /task/work/source_raw.json
univer run /task/cases/case_1/input.univer --file /task/work/filter_dates.js
univer export /task/cases/case_1/input.univer /task/outputs/case_1/output.xlsx --json
```

但实际脚本核心逻辑使用了 display value：

```javascript
const source = sheet.getRange("A6:E315").getValues();
const start = parseDate(sheet.getRange("I2").getValue());
const end = parseDate(sheet.getRange("J2").getValue());
...
sheet.getRange("I6:M295").clearContent();
sheet.getRange("I6:M295").setValues(output);
```

这导致写回时混入字符串日期、字符串金额、简化格式和错误日期解析。

## 输出差异

失败输出示例：

```text
I6 = "24/03/23"              类型: str       格式: dd/mm/yy
M6 = " 4,667.98 € "         类型: str       格式: General
I8 = 2023-05-04              类型: datetime  实际应为 2023-04-05
C列对应输出格式丢失 000000000
金额格式退化为 General 或 #,##0.00€
```

之前单题成功运行 `codex-gpt-5-5-verified400-task17-35-univeronly-20260522-1613` 的输出：

```text
I6 = 2023-03-24              类型: datetime  格式: dd/mm/yy;@
M6 = 4667.98                 类型: float     格式: 完整欧元格式
I8 = 2023-04-05              类型: datetime
C列保留 000000000
```

两次都输出 289 行，范围都是 `I6:M294`，`I295:M295` 为空；失败点不是行数，而是值类型、日期解析和格式保留。

## 根因

1. `getValues()` 返回的是显示值，不适合作为可计算数据和最终答案的来源。
   - 日期可能变成 `24/03/23` 这类字符串。
   - 金额可能变成带货币符号和空格的字符串。
   - 再用 `setValues()` 写回时，Univer/Excel 可能重新推断类型，导致日期错位或格式丢失。

2. 脚本没有复制数字格式和视觉格式。
   - 没有使用 `getNumberFormats()` / `setNumberFormats()`。
   - 没有保留编号列 `000000000`。
   - 没有稳定保留金额列完整欧元格式。

3. agent 虽然先通过 `pipe out --type rawValue` 导出了 raw 数据到 `/task/work/*.json`，但最终脚本没有使用这些 raw 文件，也没有在 `univer run` 内使用 `getRawValues()`。

4. 日志中还有一个过程问题：agent 首次执行 `univer run --file /task/work/filter_dates.js` 时脚本尚未创建，出现 `ENOENT`，随后自行恢复。这个问题没有直接导致评测失败，但属于执行顺序不稳。

## 与已修复问题的关系

此前的修复已经成功解决了“为保持格式而绕过 `.univer`，改用 `.xlsx + openpyxl/ExcelJS`”的问题。本次失败说明新的约束有效，但还需要补充一条更细的通用规则：

- 对涉及日期、金额、编号、百分比等格式化数据的筛选/复制/搬运任务，不应使用 display values 作为写回源。
- 应优先使用 raw values，并显式复制 number formats / backgrounds / relevant formatting。

## 候选改进方向

可以考虑在 agent prompt 或 `univer-cli` skill 中加入通用规则：

```text
  Univer Sheets 单元格值规则：

  1. 单元格真实模型是 ICellData，不是普通 JS 值。
     常见字段：
     - v：值
     - t：类型，1=STRING，2=NUMBER，3=BOOLEAN，4=FORCE_STRING
     - f：公式
     - p：富文本
     - s：样式/数字格式
     - custom：自定义数据

  2. getValues() 不是通用 raw 读取。
     它返回 facade/view 层值，可能受 number format、interceptor、显示逻辑影响，也不会保留 t/f/p/s/custom 等字段。
     不要把 getValues() + setValues() 当成通用读写方案。

  3. 读取时按意图选择：
     - 展示值：getValues() 或 getDisplayValues()
     - 原始值但不保留模型：getRawValues()
     - 完整单元格模型：getCellDatas()
     - 公式：getFormula() / getFormulas()

  4. 写入时按意图选择：
     - 新的简单值：可以直接写 string / number / boolean
     - 明确类型、公式、日期、格式、富文本、强制文本：写完整 ICellData
     - 公式：setFormula('=A1+B1') 或 { f: '=A1+B1' }
     - 公式文本：{ v: '=A1+B1', t: 4 }
     - 前导零/ID/编码：{ v: '00123', t: 4 }

  5. 日期、百分比、货币不是独立类型。
     它们都是 number + s.n.pattern：
     - 日期：{ v: 日期序列号, t: 2, s: { n: { pattern: 'yyyy-mm-dd' } } }
     - 百分比：{ v: 0.25, t: 2, s: { n: { pattern: '0%' } } }
     - 货币：{ v: 1234.5, t: 2, s: { n: { pattern: '$#,##0.00' } } }

  6. 从已有单元格读后再写：
     - 只要展示值：getValues()/getDisplayValues() -> setValues()
     - 只要 raw 值：getRawValues() -> setValues()
     - 要保留类型/公式/格式/富文本/自定义数据：getCellDatas() -> deep clone -> clear 目标区域 -> setValues()
     - 移动区域：优先用 move-range command 或 moveRows/moveColumns

  7. 清空单元格：
     - 清内容：clearContent()
     - 清内容和格式：clear()
     - 不要用 setValue(null)
```

如果要更偏 skill，可以补一个 recipe：

- `getRawValues()` 读取源值。
- `getNumberFormats()` 读取源数字格式。
- 必要时用 `getBackgrounds()` / `setBackgroundColor()` 保留填充色。
- `setValues()` 写 raw values。
- `setNumberFormats()` 写回格式。
- 验证导出的 `.xlsx` 中日期、金额、编号列类型和格式，而不仅验证行数。

## 风险

- 直接把所有格式复制规则写进 prompt 可能增加 token 和过度约束；更适合放进 skill recipe 或短 prompt 规则。
- Univer facade 暴露的完整样式复制能力有限，复杂格式仍需要逐项复制或通过更完善的 CLI/API 支持。
- 需要避免引入 task-specific 描述；规则应保持通用，面向“格式化数据搬运/筛选”这一类任务。
