# 262-17: univer export drawing crash 导致 TSV fallback 日期损坏

## 背景

- task-id: `262-17`
- run-id: `codex-gpt-5-5-verified400-first20-w10-cellrules-20260522-1808`
- dataset: `spreadsheetbench_verified_400`
- agent: `codex`, model `gpt-5.5`
- instruction_type: `Sheet-Level Manipulation`
- answer_position: `Sheet1'!A1:F14`
- 推理状态: `ok`
- 评测结果: `test_case_results: [0]`
- 耗时: `179.401s`

题目要求按 `Task` 升序，再按 `Responsibility` 升序，对 `Sheet1!A1:F14` 排序。题目提到 VBA/macro，但期望结果是 workbook 可见排序效果，不是把 VBA 代码写入单元格。

## 现象

agent 在原 workbook 上正确实现了排序逻辑，并通过 `pipe out` 对比了排序后的 `Sheet1` 与 `Sheet2` 预期文本：

```text
/task/work/sheet1_after.tsv
/task/work/sheet2_expected.tsv
```

排序脚本核心逻辑：

```javascript
const values = target.getValues();
const headers = values[0];
const taskIndex = headers.findIndex(... "task" ...);
const responsibilityIndex = headers.findIndex(... "responsibility" ...);

const sortedRows = values.slice(1).sort((left, right) => {
  const byTask = compareText(left[taskIndex], right[taskIndex]);
  if (byTask !== 0) return byTask;
  return compareText(left[responsibilityIndex], right[responsibilityIndex]);
});

target.setValues([headers, ...sortedRows]);
```

排序结果文本层面正确，但从原 workbook 导出 `.xlsx` 时 `univer export` 崩溃。

## export 崩溃日志

```text
file export conversion failed for /task/outputs/case_1/output.xlsx:
Command failed: /usr/local/bin/node /usr/local/lib/node_modules/univer-cli/node_modules/@univerjs-pro/uexcli/bin/cli.js export ...
panic: runtime error: invalid memory address or nil pointer dereference
[signal SIGSEGV: segmentation violation code=0x1 addr=0x18 pc=0x9ffb40]

goroutine 7 [running]:
github.com/dream-num/univer-exchange/exchange.HandleExportShapeDrawing(...)
    export_sheet_shape.go:66
github.com/dream-num/univer-exchange/exchange.ExportDrawing(...)
    sheet_drawing.go:339
github.com/dream-num/univer-exchange/exchange.(*WorksheetExportImpl).createWorksheetFile(...)
    export_sheet_worksheet.go:50
github.com/dream-num/univer-exchange/exchange.NewWorkbookExportImpl(...)
    export_sheet_workbook.go:24
github.com/dream-num/univer-exchange/exchange.NewExcelXmlFile(...)
    export_sheet_excel.go:198
```

栈里明确指向 drawing/shape export：

- `HandleExportShapeDrawing`
- `ExportDrawing`
- `export_sheet_shape.go`
- `sheet_drawing.go`

这说明原 workbook 的导出失败是 `univer export` / `univer-exchange` 的 drawing 导出崩溃，不是排序逻辑本身失败。

## agent fallback

为绕过 export crash，agent 创建了 clean workbook：

```text
/task/work/clean_case_1.univer
```

然后用文本中转：

```text
univer pipe in /task/work/clean_case_1.univer --range 'Sheet1'!A1:F14 --input-format tsv --data-file /task/work/sheet1_after.tsv
univer pipe in /task/work/clean_case_1.univer --range 'Sheet2'!A1:F20 --input-format tsv --data-file /task/work/sheet2_full.tsv
univer export /task/work/clean_case_1.univer /task/outputs/case_1/output.xlsx --json
```

这个 workaround 成功生成了 output.xlsx，但引入了日期损坏。

## fallback 日期损坏

Golden 中的日期：

```text
2022-02-01, 2022-08-01
2022-01-10, 2022-12-01
```

Output 中变成：

```text
2022-01-02, 2022-01-08
2022-10-01, 2022-01-12
```

也就是：

- `02/01/2022` 被解释为 2022-01-02，而不是 2022-02-01。
- `10/01/2022` 被解释为 2022-10-01，而不是 2022-01-10。
- `12/01/2022` 被解释为 2022-01-12，而不是 2022-12-01。

这是典型的 display TSV 日期歧义。文本通道丢失了原始日期 serial 和 number format，clean workbook 导入时重新猜测日期格式，导致 MM/DD 与 DD/MM 混淆。

## 根因分层

1. 根本问题：`univer export` 在原 workbook 上因 drawing/shape 导出 panic 崩溃。
2. 次生问题：agent 的 clean workbook fallback 使用 TSV/display value 搬运数据，导致日期类型和格式丢失。
3. 排序逻辑本身基本正确，且 VBA/macro prompt 规则生效：agent 实现了 workbook 可见排序效果，没有把 VBA 代码写入单元格。

## 影响

- 即使 workbook 可见编辑正确，只要原 workbook 含触发崩溃的 drawing/shape，最终 `.xlsx` 无法由原 workbook 导出。
- agent 为绕过 export crash 使用文本重建 workbook 时，会破坏日期、货币、百分比、前导零等格式化数据。
- 这类失败会表现为评测值差异，而真实根因可能是 export 崩溃触发了不安全 fallback。

## 候选改进方向

### CLI / Univer 侧

- 修复 `univer-exchange` drawing export 的 nil pointer：`HandleExportShapeDrawing` / `ExportDrawing` 应能处理缺失 drawing/shape 结构。
- 给 `univer export` 增加更可诊断的错误信息，至少标出具体 sheet/drawing 对象。
- 如果 drawing export 可选，考虑提供跳过 drawing 的安全导出参数，例如 `--skip-drawings` 或类似能力。

### agent / skill 侧

- 如果 `univer export` 因 drawing/shape 崩溃，不应直接用 display TSV 重建 workbook。
- 必须 fallback 重建时，应使用 raw/model 数据：日期用 serial + number format，必要时用 `getCellDatas()` 深拷贝单元格模型。
- 对日期、货币、百分比、前导零 ID 等格式化数据，禁止以 display TSV 作为最终搬运格式。

## 风险

- agent workaround 可以掩盖真正的 CLI export bug，使问题表面看起来像日期处理错误。
- 直接提示 agent 避免 fallback 可能导致没有 output.xlsx；但不安全 fallback 会生成错误文件，评测同样失败。
- 这个问题应该优先作为 CLI/export issue 跟进，而不是单纯加 prompt 规则。
