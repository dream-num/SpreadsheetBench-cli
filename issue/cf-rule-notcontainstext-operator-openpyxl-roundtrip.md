# univer export 将条件格式 `notContainsText` 写入非法 operator

## GitHub issue

- URL: https://github.com/dream-num/univer-cli/issues/317
- 标题：`bug: import/export roundtrip 将 notContainsText 写入非法 cfRule operator`
- 目标仓库：`dream-num/univer-cli`

## 问题描述

`univer import` + `univer export` roundtrip 后，导出的 `.xlsx` 在条件格式规则中出现：

```xml
<cfRule type="notContainsText" operator="notContainsText" ...>
```

`notContainsText` 可以作为条件格式 rule type，但不是合法的 `operator` 值。`openpyxl` 读取导出文件时会在 worksheet 解析阶段失败，导致文件无法被依赖严格 OOXML 解析器的流程读取。

## 实际表现

roundtrip 命令成功：

```bash
univer import input.xlsx repro.univer --json
univer export repro.univer exported.xlsx --json
```

但 `openpyxl.load_workbook("exported.xlsx")` 失败：

```text
ValueError: Unable to read workbook: could not read worksheets from exported.xlsx.
This is most probably because the workbook source files contain some invalid XML.

ValueError: Value must be one of {'notEqual', 'beginsWith', 'notBetween', 'greaterThanOrEqual', 'equal', 'notContains', 'lessThanOrEqual', 'endsWith', 'greaterThan', 'lessThan', 'containsText', 'between'}
```

## 非法 XML 节点

导出的 `xl/worksheets/sheet1.xml` 中有两条同类规则：

```xml
<cfRule priority="19" type="notContainsText" dxfId="18" operator="notContainsText" text="Month">
  <formula>ISERROR(SEARCH("Month",BD15))</formula>
</cfRule>
```

```xml
<cfRule priority="79" type="notContainsText" dxfId="78" operator="notContainsText" text="Month">
  <formula>ISERROR(SEARCH("Month",BD3))</formula>
</cfRule>
```

对应条件格式范围：

```text
BD15
BD3:BD14 BD16:BD20
```

## 期望表现

导出的 `.xlsx` 应能被 `openpyxl` 正常读取。

对于 `type="notContainsText"` 的条件格式，导出时不应把 `operator` 写成 `notContainsText`。可选方向：

- 如果 OOXML 对该 rule type 不需要 `operator`，则省略 `operator` 属性。
- 如果需要兼容 openpyxl 的枚举，应映射为合法值，例如 `operator="notContains"`。

具体应以 OOXML 规范和 Excel 兼容行为为准。

## 最小复现步骤

复现需要附件中的 `input.xlsx`。

```bash
univer import input.xlsx repro.univer --json
univer export repro.univer exported.xlsx --json
```

验证：

```python
from openpyxl import load_workbook

load_workbook("input.xlsx")     # OK
load_workbook("exported.xlsx")  # Fails
```

检查导出 XML：

```bash
unzip -p exported.xlsx xl/worksheets/sheet1.xml | grep notContainsText
```

## 已验证的根因线索

源文件中没有非法的 `operator="notContainsText"` 节点；该节点是 `univer import` 后再 `univer export` 引入的。

本地批量验证中：

```text
task-id: 54590
input:  openpyxl_error, sheet1.xml 中 2 个 cfRule operator="notContainsText"
output: openpyxl_error, sheet1.xml 中 2 个 cfRule operator="notContainsText"
```

## 附件 / 复现文件

本地已准备复现包：

```text
debug/univer-cf-rule-notcontainstext-operator-repro.zip
```

包内包含：

```text
input.xlsx
exported.xlsx
README.md
```

其中：

- `input.xlsx` 是源文件，`openpyxl` 可读取。
- `exported.xlsx` 是 `univer import` 后不做任何编辑、直接 `univer export` 得到的文件，`openpyxl` 读取失败。

当前 `gh issue create/comment/edit` 不能直接上传附件，需要手动上传到 GitHub issue。

## 关联背景：SpreadsheetBench

这个问题是在验证 SpreadsheetBench Verified 400 的 xlsx import/export roundtrip 时发现的。

关联任务：

```text
dataset: spreadsheetbench_verified_400
task-id: 54590
```

本地验证结果：

```text
.runs/cli-roundtrip-ver400-openpyxl-error-keep-20260526-120117
```
