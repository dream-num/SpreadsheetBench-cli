## 问题描述

`univer import` 导入一个 `.xlsx` 后，`Sheet1!C3` 的公式计算值错误。

原始文件在 Excel 和 WPS 中打开时，`Sheet1!C3` 显示为 `16/01/2009`。用 `openpyxl.load_workbook(..., data_only=True)` 读取原始 `.xlsx`，`C3` 也有非空日期值。

导入为 `.univer` 后，同一单元格保留了公式文本，但 workbook 可见计算值变为空字符串。

本 issue 只以 `Sheet1!C3` 单元格为例，不展开其它依赖单元格。

## 复现文件

参考附件 `33157-import-formula-cache-date-loss.zip`，其中包含：

- `1_33157_init.xlsx`
- `README.md`

## 复现步骤

```bash
univer daemon stop
univer import 1_33157_init.xlsx 33157-init.univer --json
univer run 33157-init.univer --code '() => {
  const wb = univerAPI.getActiveWorkbook();
  const s = wb.getSheetByName("Sheet1");
  return {
    success: true,
    values: s.getRange("C3").getValues(),
    display: s.getRange("C3").getDisplayValues(),
    formulas: s.getRange("C3").getFormulas(),
    cellDatas: s.getRange("C3").getCellDatas()
  };
}'
```

## 期望表现

导入后的 `.univer` 中，`Sheet1!C3` 的计算值应与原始 Excel 文件中的计算结果一致，不应为空字符串。

原始文件在 Excel 和 WPS 中该单元格显示为：

```text
16/01/2009
```

## 实际表现

导入后的 `.univer` 中，`Sheet1!C3`：

```text
formula = =IFERROR(VALUE(REPLACE(B3,11,500,"")),"")
value = ""
```

关键输出：

```json
{
  "values": [[""]],
  "display": [[""]],
  "formulas": [["=IFERROR(VALUE(REPLACE(B3,11,500,\"\")),\"\")"]],
  "cellDatas": [[{
    "f": "=IFERROR(VALUE(REPLACE(B3,11,500,\"\")),\"\")",
    "v": "",
    "t": 1
  }]]
}
```

## 影响

下游流程读取 `.univer` 时会看到错误的 workbook 可见计算值，导致依赖该单元格结果的后续操作出现偏差。

## 关联背景

该问题是在 SpreadsheetBench `spreadsheetbench_verified_400` 的 task `33157` 中发现的。

本地记录：`issue/33157-import-formula-c3-calculation-wrong.md`
