# 41978 empty sheetData export repro

## Reproduce

```bash
univer import input.xlsx repro.univer --json
univer export repro.univer exported.xlsx
```

Verify with `openpyxl` and worksheet XML:

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

## Observed

```text
input    B1=Last Name  G1=Year  nonempty=555  dims=(185, 13)  xml_rows=185  xml_cells=1849
exported B1=None       G1=None  nonempty=0    dims=(144, 11)  xml_rows=181  xml_cells=0
```

`univer import` and `univer export` both return success, but the exported workbook loses all worksheet cell nodes.
