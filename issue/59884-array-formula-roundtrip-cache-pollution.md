# 59884 import 后 array formula 计算值错误

## 摘要

`univer import` 导入 `spreadsheetbench_verified_400` task `59884` 后，`Sheet1` 中 array formula 的可见计算结果与 Excel 不一致。

该问题会影响 `openpyxl.load_workbook(..., data_only=True)` 的评测值，也会误导 agent：最新失败 run 中，agent 编辑前已经从 `.univer` 读到了污染后的 `G2:G5`，随后基于错误 workbook-visible state 写入输出。

## 复现环境

- 仓库：`/Users/otime/project/SpreadsheetBench-cli`
- 数据集：`spreadsheetbench_verified_400`
- task id：`59884`
- `univer --version`：`0.0.0`
- 复现日期：`2026-05-26`
- 上游 issue：`https://github.com/dream-num/univer-cli/issues/330`

## 原始文件与人工验证

原始文件：

```text
data/spreadsheetbench_verified_400/spreadsheet/59884/1_59884_init.xlsx
```

在 Microsoft Excel 中打开原始文件并手动重算后，`Sheet1!G1:O5` 保持如下结果：

```text
G1 = 1st
H1 = Occurances
I1 = 2nd ->

G2 = 0
H2 = 0
I2:O2 = 空

G3 = 1
H3 = 3
I3 = a
J3 = b
K3 = c
L3:O3 = 空

G4 = 2
H4 = 4
I4:O4 = 空

G5 = 3
H5 = 5
I5:O5 = 空
```

这说明原始 `.xlsx` 的 Excel 计算结果不是缓存陈旧导致的。

## 相关公式

`Sheet1!G2` 是 array formula：

```excel
=IF({1,0},_xlfn._xlws.SORT(_xlfn.UNIQUE($A$2:$A$1000)),SUMIFS($C$2:$C$1000,$A$2:$A$1000,_xlfn._xlws.SORT(_xlfn.UNIQUE($A$2:$A$1000))))
```

原始 `data_only=True` 关键值：

```text
G2 = 0
G3 = 1
I2 = 空
I3 = a
```

## import-only 复现

```bash
univer import data/spreadsheetbench_verified_400/spreadsheet/59884/1_59884_init.xlsx \
  .runs/tmp-import-only-check/59884.univer --json
univer pipe out .runs/tmp-import-only-check/59884.univer --range 'Sheet1!G1:O5' --format tsv
```

实际输出：

```text
1st    Occurances    2nd ->
1      3
2      4             a    b    c
3      5
0      0
```

这与 Excel 期望的 `G2=0, H2=0, I2:O2=空, G3=1, H3=3, I3=a` 不一致。

扫描结果 `.runs/cli-roundtrip-ver400-abnormal-20260526-143009/results.csv` 也记录了同一问题：

```text
59884 input  Sheet1!G2  src=0  exported=1
59884 output Sheet1!G2  src=0  exported=1
```

分类为 `abnormal_formula_changed_at_value_cell`。

## 对 agent 失败的影响

最新相关 run：

```text
codex-gpt-5-5-high-verified400-wrong86-w8-20260526-150018
```

该 run 中 agent 在编辑前读取 `G1:O5` 时已经看到污染后的 `G2=1`、`G5=0`，随后按错误的 `G2:G5` 状态写入 `I2:O5`，导致输出整体上移并评测失败。

## 期望表现

`univer import` 后的 workbook-visible state 应与 Excel 打开并重算后的结果一致。至少 `Sheet1!G2` 应保持为 `0`，`Sheet1!I2:O2` 应保持空白。

## 实际表现

import 后 `Sheet1!G2` 从 `0` 变为 `1`，后续结果区域整体上移。

## 归因

这是 `univer-cli` / Univer 对 array formula / dynamic array 公式导入或计算处理不兼容导致的工具链问题，不是 agent 题意理解错误。

## 关联背景

该问题来自 SpreadsheetBench `spreadsheetbench_verified_400` task `59884`：

- 矩阵中多次 FAIL。
- 最新 high run 仍 FAIL。
- 本地 Excel 人工打开并手动计算后，原始 workbook 与期望结果一致。
