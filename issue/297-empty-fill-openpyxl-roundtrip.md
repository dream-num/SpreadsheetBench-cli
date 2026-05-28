# Issue 297: import/export roundtrip 生成空 fill 导致 openpyxl 无法读取 xlsx

## GitHub issue

- URL: https://github.com/dream-num/univer-cli/issues/297
- 标题：`bug: import/export roundtrip 生成空 fill 导致 openpyxl 无法读取 xlsx`
- 目标仓库：`dream-num/univer-cli`

## 问题描述

某些 `.xlsx` 文件本身可以被 Microsoft Excel 和 `openpyxl` 正常打开；但经过 `univer import` 再 `univer export` 后，导出的 `.xlsx` 中 `xl/styles.xml` 会出现空的 `<fill/>` 节点。

Microsoft Excel 可以打开导出文件，但 `openpyxl.load_workbook()` 会失败：

```text
TypeError: expected <class 'openpyxl.styles.fills.Fill'>
```

这会影响依赖 `openpyxl` 或严格 OOXML 解析器读取导出文件的流程。

## 最小复现

复现包附件：`univer-empty-fill-openpyxl-repro.zip`

附件内容：

```text
input.xlsx
```

复现步骤：

```bash
univer import input.xlsx repro.univer --json
univer export repro.univer exported.xlsx
```

用 `openpyxl` 验证：

```python
from openpyxl import load_workbook

for path in ["input.xlsx", "exported.xlsx"]:
    print("checking", path)
    try:
        load_workbook(path)
        print("ok")
    except Exception as e:
        print(type(e).__name__, e)
```

实际结果：

```text
checking input.xlsx
ok
checking exported.xlsx
TypeError expected <class 'openpyxl.styles.fills.Fill'>
```

检查 `styles.xml`：

```python
from zipfile import ZipFile
import re

for path in ["input.xlsx", "exported.xlsx"]:
    with ZipFile(path) as z:
        styles = z.read("xl/styles.xml").decode("utf-8", errors="replace")
    fill_count = re.search(r'<fills[^>]*count="(\d+)"', styles)
    empty_fill_count = styles.count("<fill/>") + styles.count("<fill />")
    print(path, "fills", fill_count.group(1) if fill_count else "?", "empty_fill", empty_fill_count)
```

实际结果：

```text
input.xlsx fills 35 empty_fill 0
exported.xlsx fills 11 empty_fill 1
```

## 已验证的更多样例

以下多个 SpreadsheetBench 文件都能复现同类问题：源文件可被 `openpyxl` 读取，roundtrip 导出后出现空 `<fill/>` 并导致 `openpyxl` 读取失败。

```text
51090: exported fills=25, empty_fill=4
3911:  exported fills=12, empty_fill=1
35742: exported fills=23, empty_fill=3
52541: exported fills=20, empty_fill=7
55060: exported fills=11, empty_fill=1
57989: exported fills=23, empty_fill=5
```

## SpreadsheetBench 影响

在 SpreadsheetBench runner 中，评测程序使用 `openpyxl.load_workbook(..., data_only=True)` 读取导出结果，因此这类文件会在进入单元格值比较前直接失败。

关联错题包括：

- `193-51090`
- `215-3911`
- `258-35742`
- `315-52541`
- `332-55060`
- `384-57989`

## 当前复测状态

截至 `2026-05-28`，错题矩阵中该 issue 关联的 6 个 task 在最近两次 codex gpt-5.5 报告中均已通过：

```text
20260527-220546: 3911 PASS, 35742 PASS, 51090 PASS, 52541 PASS, 55060 PASS, 57989 PASS
allwrong96-exskip-w5-timeout480-20260527-232251: 3911 PASS, 35742 PASS, 51090 PASS, 52541 PASS, 55060 PASS, 57989 PASS
```

这说明当前 SpreadsheetBench agent 输出路径下这些 task 已不再因该已知现象失败；不等同于上游 import/export roundtrip 问题已经消失，若需要关闭上游 issue 仍应用最小复现包重新验证。

## 附件状态

本地已准备复现包：

```text
debug/univer-empty-fill-openpyxl-repro.zip
```

当前 `gh issue create/comment/edit` 不能直接上传附件，需要手动上传到 GitHub issue。
