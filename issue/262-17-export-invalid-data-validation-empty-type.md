# 262-17: univer export 将无类型 dataValidation 导出为非法 type=""

## 背景

- task-id: `262-17`
- run-id: `codex-gpt-5-5-verified400-first80-20260523-163607`
- dataset: `spreadsheetbench_verified_400`
- agent: `codex`, model `gpt-5.5`
- instruction_type: `Sheet-Level Manipulation`
- answer_position: `Sheet1'!A1:F14`
- 推理状态: `ok`
- 评测结果: `test_case_results: [0]`
- 耗时: `131.32s`

题目要求对 `Sheet1!A1:F14` 按动态定位到的 `Task` 和 `Responsibility` 两列升序排序。当前 run 的最终输出在单元格值层面与 golden 一致，但导出的 `.xlsx` 含非法 data validation XML，导致 `openpyxl` 无法读取 workbook，评测失败。

## 现象

当前输出：

```text
data/spreadsheetbench_verified_400/outputs/univer_agent_gpt-5.5/1_262-17_output.xlsx
```

用 XML 直接解析 `Sheet1!A1:F14`，output 与 golden 单元格值一致：

```text
value compare Sheet1 A1:F14 output XML vs golden display-ish raw
diff_count 0
```

但 `openpyxl.load_workbook()` 读取 output 失败：

```text
ValueError: Unable to read workbook: could not read worksheets from data/spreadsheetbench_verified_400/outputs/univer_agent_gpt-5.5/1_262-17_output.xlsx.
This is most probably because the workbook source files contain some invalid XML.
ValueError: Value must be one of {'decimal', 'textLength', 'custom', 'whole', 'list', 'date', 'time'}
```

根因 XML 在 `xl/worksheets/sheet1.xml`：

```xml
<dataValidation type="" error="Date Format should be DD-MM-YYYY" prompt="Date Format should be DD-MM-YYYY" errorTitle="Invalid Date Format" promptTitle="Invalid Date Format" showInputMessage="1" showErrorMessage="1" sqref="D1:E1"/>
```

OOXML 中空字符串不是合法 data validation `type`。原始 xlsx / golden 对同一个 rule 的表示是省略 `type` 属性，而不是写 `type=""`。

## 独立复现

复现目录：

```text
debug-tmp/data-validation-empty-type-repro/
```

复现文件：

```text
debug-tmp/data-validation-empty-type-repro/input.xlsx
debug-tmp/data-validation-empty-type-repro/input.univer
debug-tmp/data-validation-empty-type-repro/exported.xlsx
```

复现步骤不依赖 agent 排序脚本，也不修改 workbook 内容，只做 import + export：

```bash
mkdir -p debug-tmp/data-validation-empty-type-repro
cp .runs/univer-agent/codex-gpt-5-5-verified400-first80-20260523-163607/262-17/task/cases/case_1/input.xlsx debug-tmp/data-validation-empty-type-repro/input.xlsx
univer import debug-tmp/data-validation-empty-type-repro/input.xlsx debug-tmp/data-validation-empty-type-repro/input.univer --json
univer export debug-tmp/data-validation-empty-type-repro/input.univer debug-tmp/data-validation-empty-type-repro/exported.xlsx --json
```

实际结果：

```text
univer import ... -> success true
univer export ... -> success true
```

原始输入可被 `openpyxl` 读取：

```text
input: openpyxl_ok ['Sheet1', 'Sheet2']
```

导出文件无法被 `openpyxl` 读取：

```text
exported: openpyxl_error ValueError Unable to read workbook: could not read worksheets from debug-tmp/data-validation-empty-type-repro/exported.xlsx.
```

原始 `input.xlsx` 的 `xl/worksheets/sheet1.xml` 中，第一条 data validation 没有 `type` 属性：

```xml
<dataValidation showInputMessage="1" showErrorMessage="1" errorTitle="Invalid Date Format" error="Date Format should be DD-MM-YYYY" promptTitle="Date Format should be DD-MM-YYYY" sqref="D1:E1" .../>
```

经 `univer import` + `univer export` 后，`exported.xlsx` 变成非法空类型：

```xml
<dataValidation type="" error="Date Format should be DD-MM-YYYY" prompt="Date Format should be DD-MM-YYYY" errorTitle="Invalid Date Format" promptTitle="Invalid Date Format" showInputMessage="1" showErrorMessage="1" sqref="D1:E1"/>
```

## 根因判断

这是 `univer-cli` / export 链路问题，不是 agent 排序内容错误：

1. 不编辑 workbook，仅 import + export 即可复现。
2. 输入 xlsx 合法，`openpyxl` 可读。
3. 输出 xlsx 中 `dataValidation type=""` 非法，`openpyxl` 无法读取。
4. 当前失败 case 的 `Sheet1!A1:F14` 单元格值与 golden 一致，失败核心是导出文件结构兼容性。

## 与旧 issue 的关系

旧 issue：

```text
issue/262-17-export-drawing-crash-date-fallback.md
```

记录的是早期 `univer export` drawing/shape nil pointer panic，以及 agent fallback 导致日期损坏。当前问题不同：

- drawing export crash 已在后续版本修复。
- 现在 export 命令返回成功。
- 新问题是导出的 xlsx 含非法 data validation XML。

因此本 issue 应独立跟踪。

## 候选修复方向

CLI / export 侧：

- 当 data validation rule 的 type 为空或未设置时，导出 OOXML 应省略 `type` 属性。
- 不应导出 `type=""`。
- 增加回归测试：导入包含无 `type` data validation 的 xlsx 后再导出，导出的 xlsx 应能被 `openpyxl` 读取。

评测 / runner 侧：

- 对这类失败应记录 openpyxl 读取失败的底层 XML 原因，避免误判为 agent 内容错误。

agent / prompt 侧：

- 这不是 agent 可稳定规避的问题。即使 agent 正确编辑并验证 workbook-visible 值，最终 `univer export` 仍可能生成非法 xlsx。
