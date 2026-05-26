# 33157 import formula C3 calculation wrong

## 摘要

`univer import` 导入 `spreadsheetbench_verified_400` 的 task `33157` 输入文件后，`Sheet1!C3` 的公式计算值错误。

本地复现中，原始 `1_33157_init.xlsx` 的 `Sheet1!C3` 在 Excel/openpyxl `data_only=True` 下有非空日期值；重新导入后的 `.univer` 中，同一单元格保留了公式文本，但 workbook 可见计算值为空字符串。

在 Excel 和 WPS 中打开原始 `.xlsx` 时，`Sheet1!C3` 单元格显示为 `16/01/2009`。

本 issue 只记录 `Sheet1!C3` 这个单元格，不展开其它依赖单元格。

## 复现环境

- 仓库：`/Users/otime/project/SpreadsheetBench-cli`
- 数据集：`spreadsheetbench_verified_400`
- task id：`33157`
- `univer --version`：`0.0.0`
- 复现日期：`2026-05-26`

## 复现步骤

先重启 daemon：

```bash
univer daemon stop
```

确认原始 `.xlsx` 中 `C3` 的结果：

```bash
.venv/bin/python - <<'PY'
import openpyxl
p='data/spreadsheetbench_verified_400/spreadsheet/33157/1_33157_init.xlsx'
wb=openpyxl.load_workbook(p, data_only=True)
ws=wb['Sheet1']
print('B3', repr(ws['B3'].value))
print('C3', repr(ws['C3'].value))
PY
```

实际输出：

```text
B3 '16/01/2009 - Plumbing - Pluto'
C3 datetime.datetime(2009, 1, 16, 0, 0)
```

重新导入为 `.univer`：

```bash
mkdir -p .runs/tmp-33157-repro-3
univer import data/spreadsheetbench_verified_400/spreadsheet/33157/1_33157_init.xlsx \
  .runs/tmp-33157-repro-3/33157-init.univer --json
```

读取导入后的 `C3`：

```bash
univer run .runs/tmp-33157-repro-3/33157-init.univer --code '() => {
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

## 期望表现

导入后的 `.univer` 中，`Sheet1!C3` 的计算值应与原始 Excel 文件中的计算结果一致，不应为空字符串。原始文件在 Excel 和 WPS 中该单元格显示为 `16/01/2009`。

## 实际表现

导入后的 `.univer` 中，`Sheet1!C3`：

```text
formula = =IFERROR(VALUE(REPLACE(B3,11,500,"")),"")
value = ""
```

## 影响

下游流程读取 `.univer` 时会看到错误的 workbook 可见计算值，导致依赖该单元格结果的后续操作出现偏差。

## 关联背景

该问题是在 SpreadsheetBench `spreadsheetbench_verified_400` 的 task `33157` 中发现的。相关运行分析记录见：

- `ai-analyze/codex-gpt-5-5-verified400-all-20260525-223740/255-33157.md`
