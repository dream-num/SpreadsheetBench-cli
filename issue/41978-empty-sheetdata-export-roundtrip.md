# 41978: import/export roundtrip 导出空 sheetData

## GitHub issue

- URL: https://github.com/dream-num/univer-cli/issues/320
- 标题：`bug: import/export roundtrip 后 worksheet sheetData 丢失所有单元格`
- 目标仓库：`dream-num/univer-cli`

## 问题描述

某个 `.xlsx` 文件可以被 `openpyxl` 正常读取，源文件 worksheet 中有正常的单元格值、公式、样式和合并单元格。执行最小 `univer import` + `univer export` roundtrip 后，CLI 命令均返回成功，但导出的 `.xlsx` 中 `xl/worksheets/sheet1.xml` 的 `sheetData` 只剩 row 节点，没有任何 cell 节点。

结果是导出文件的工作表内容整体为空；例如源文件 `Cumulative!B1` 为 `Last Name`，导出后为 `None`。

## 最小复现

复现包附件：`41978-empty-sheetdata-export-repro.zip`

附件内容：

```text
input.xlsx
README.md
```

复现步骤：

```bash
univer import input.xlsx repro.univer --json
univer export repro.univer exported.xlsx
```

用 `openpyxl` 和 worksheet XML 验证：

```python
from openpyxl import load_workbook
import zipfile
import xml.etree.ElementTree as ET

ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

for label, path in [("input", "input.xlsx"), ("exported", "exported.xlsx")]:
    wb = load_workbook(path, data_only=False)
    ws = wb["Cumulative"]
    nonempty = sum(1 for row in ws.iter_rows() for cell in row if cell.value is not None)
    print(label, "B1=", ws["B1"].value, "G1=", ws["G1"].value, "nonempty=", nonempty, "dims=", (ws.max_row, ws.max_column))

    data = zipfile.ZipFile(path).read("xl/worksheets/sheet1.xml")
    root = ET.fromstring(data)
    rows = root.findall(".//x:sheetData/x:row", ns)
    cells = root.findall(".//x:sheetData/x:row/x:c", ns)
    print(label, "xml_rows=", len(rows), "xml_cells=", len(cells))
```

实际结果：

```text
input    B1=Last Name  G1=Year  nonempty=555  dims=(185, 13)  xml_rows=185  xml_cells=1849
exported B1=None       G1=None  nonempty=0    dims=(144, 11)  xml_rows=181  xml_cells=0
```

## 期望表现

Roundtrip 导出的 `.xlsx` 应保留 worksheet 单元格内容。至少源文件中已有的文本、数值、公式和可见工作表结构不应在 `univer export` 后整体丢失。

## 已验证线索

- `univer import` 返回成功。
- `univer export` 返回成功。
- 导出文件仍保留部分 worksheet 布局信息，例如行高、合并区域、冻结窗格等。
- 导出文件的 `xl/worksheets/sheet1.xml` 中存在 row 节点，但没有任何 `<c>` 单元格节点。
- 同一个文件在 SpreadsheetBench agent 运行中，agent 在 `.univer` 内部可以读写并验证目标公式；失败发生在最终导出的 `.xlsx`。
- 2026-05-26 本地验证过一个重要回归线索：回退 `dream-num/univer-cli#309` 后，本 issue 的空 `sheetData` 现象变好，roundtrip 文件重新保留 `Cumulative!B1=Last Name`、`G1=Year`，且 `xml_cells=1849`；但直接回退会导致 `dream-num/univer-cli#296` 对应的 `FILTER` 动态数组导出问题重新出现。因此这两个导出问题可能存在修复回归关联，不能简单通过回退 #309 解决。
- 当前未回退代码状态下，该问题仍表现为空 `sheetData`。

## SpreadsheetBench 关联背景

该问题是在 SpreadsheetBench Verified 400 的 task `41978` 中发现。

- dataset: `spreadsheetbench_verified_400`
- task-id: `41978`
- 失败 run-id: `codex-gpt-5-5-verified400-wrong64-rerun-w10-20260526-100513`
- 相关现象：评测读取导出的 `output.xlsx` 时，`Cumulative!I2:I11` 为空；进一步检查发现不仅目标区域为空，整个 worksheet 都没有单元格值。
- 本地复现输出：`.runs/repro-41978-simple/41978-init.roundtrip.xlsx`

SpreadsheetBench 只是发现来源；上面的附件和命令已能独立复现 `import/export` 后 worksheet cell 节点整体丢失的问题。

## 附件状态

本地已准备复现包目录：

```text
debug/41978-empty-sheetdata-export-repro/
```

当前 `gh issue create/comment/edit` 不能直接上传附件，需要手动上传 `41978-empty-sheetdata-export-repro.zip` 到 GitHub issue。
