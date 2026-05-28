# univer export 将无类型 dataValidation 导出为非法 `type=""`

## 问题描述

`univer export` 在导出包含 data validation 的 `.xlsx` 工作簿时，会把源文件中没有显式 `type` 属性的 data validation 规则导出为：

```xml
<dataValidation type="" .../>
```

但 `type=""` 不是合法的 OOXML data validation 类型。源文件中的这条规则是省略 `type` 属性，这是合法表示；导出后写成空字符串会导致严格的 XLSX 读取器无法读取工作簿。

## 实际表现

`univer import` 和 `univer export` 都返回成功：

```bash
univer import input.xlsx input.univer --json
univer export input.univer exported.xlsx --json
```

但导出的 `exported.xlsx` 中，`xl/worksheets/sheet1.xml` 包含非法 XML：

```xml
<dataValidation type="" error="Date Format should be DD-MM-YYYY" prompt="Date Format should be DD-MM-YYYY" errorTitle="Invalid Date Format" promptTitle="Invalid Date Format" showInputMessage="1" showErrorMessage="1" sqref="D1:E1"/>
```

使用 `openpyxl` 读取导出文件会失败：

```text
ValueError: Unable to read workbook: could not read worksheets from exported.xlsx.
This is most probably because the workbook source files contain some invalid XML.

ValueError: Value must be one of {'decimal', 'textLength', 'custom', 'whole', 'list', 'date', 'time'}
```

## 期望表现

如果源文件中的 data validation rule 没有显式 `type`，导出的 OOXML 应该同样省略 `type` 属性。

期望类似：

```xml
<dataValidation showInputMessage="1" showErrorMessage="1" errorTitle="Invalid Date Format" error="Date Format should be DD-MM-YYYY" promptTitle="Date Format should be DD-MM-YYYY" sqref="D1:E1"/>
```

不应导出为：

```xml
<dataValidation type="" .../>
```

导出的 `.xlsx` 应能被 `openpyxl` 等 Excel-compatible parser 正常读取。

## 最小复现步骤

复现需要附件中的 `input.xlsx`。

```bash
univer import input.xlsx input.univer --json
univer export input.univer exported.xlsx --json
```

检查 worksheet XML：

```bash
unzip -p input.xlsx xl/worksheets/sheet1.xml | grep dataValidation
unzip -p exported.xlsx xl/worksheets/sheet1.xml | grep dataValidation
```

也可以用 `openpyxl` 验证：

```python
from openpyxl import load_workbook

load_workbook("input.xlsx")      # OK
load_workbook("exported.xlsx")   # Fails
```

本地实际验证结果：

```text
input: openpyxl_ok ['Sheet1', 'Sheet2']
exported: openpyxl_error ValueError Unable to read workbook: could not read worksheets from exported.xlsx.
```

## 根因线索

源文件中 `D1:E1` 上有一条 data validation rule，它没有 `type` 属性：

```xml
<dataValidation showInputMessage="1" showErrorMessage="1" errorTitle="Invalid Date Format" error="Date Format should be DD-MM-YYYY" promptTitle="Date Format should be DD-MM-YYYY" sqref="D1:E1" .../>
```

经过 `univer import` + `univer export` 后，这条 rule 变成：

```xml
<dataValidation type="" error="Date Format should be DD-MM-YYYY" prompt="Date Format should be DD-MM-YYYY" errorTitle="Invalid Date Format" promptTitle="Invalid Date Format" showInputMessage="1" showErrorMessage="1" sqref="D1:E1"/>
```

这看起来是 export serialization 问题：未设置或空的 validation type 应该在导出 OOXML 时省略，而不是序列化为空字符串。

## 影响范围

即使 `univer export` 返回成功，导出的 `.xlsx` 也可能无法被严格的 XLSX consumer 读取，例如 `openpyxl`。

这会影响依赖导出文件做后续校验、评测或自动处理的工作流。

## 附件 / 复现文件

本地已准备复现包：

```text
debug-tmp/data-validation-empty-type-repro/repro-files.zip
```

包内包含：

```text
input.xlsx
exported.xlsx
```

其中：

- `input.xlsx` 是源文件，`openpyxl` 可读取。
- `exported.xlsx` 是 `univer import` 后不做任何编辑、直接 `univer export` 得到的文件，`openpyxl` 读取失败。

## 关联背景：SpreadsheetBench

这个问题是在分析 SpreadsheetBench 任务 `262-17` 时发现的。

关联 run：

```text
run-id: codex-gpt-5-5-verified400-first80-20260523-163607
task-id: 262-17
```

该任务中，最终输出的 `Sheet1!A1:F14` 单元格值与 golden 完全一致；直接解析 XML 对比时 `diff_count=0`。但评测失败，因为导出的 `.xlsx` 无法被 `openpyxl` 读取。

本地详细记录：

```text
issue/262-17-export-invalid-data-validation-empty-type.md
```

## 当前复测状态

截至 `2026-05-28`，错题矩阵中 `262-17` 在最近两次 codex gpt-5.5 报告中均已通过：

```text
20260527-220546: PASS
allwrong96-exskip-w5-timeout480-20260527-232251: PASS
```

这说明当前 SpreadsheetBench agent 输出路径下 `262-17` 已不再因该已知现象失败；不等同于上游 export 序列化问题已经消失，若需要关闭上游 issue 仍应用最小复现包重新验证。
