# 14240 import 后外部依赖公式结果变为 #NAME?

## 摘要

`univer import` 导入 `spreadsheetbench_verified_400` task `14240` 后，`Sheet1!U1` 的可见计算结果与 Excel 不一致。Excel 中为 `0` 的结果在 `.univer` 中变为 `#NAME?`。

该 workbook 涉及外部数据源或外部引用依赖，因此此问题应单独标注为“外部依赖场景下的公式缓存/兼容性问题”，不要与纯本地公式计算问题混为一类。

## 复现环境

- 仓库：`/Users/otime/project/SpreadsheetBench-cli`
- 数据集：`spreadsheetbench_verified_400`
- task id：`14240`
- `univer --version`：`0.0.0`
- 复现日期：`2026-05-26`
- 上游 issue：`https://github.com/dream-num/univer-cli/issues/331`

## 原始文件与人工验证

原始文件：

```text
data/spreadsheetbench_verified_400/spreadsheet/14240/1_14240_init.xlsx
```

在 Microsoft Excel 中打开原始文件并手动重算后，关键单元格保持：

```text
Sheet1!U1 = 0
Sheet1!U4 = #VALUE!
Sheet1!U5 = 0
Sheet1!U75 = 0
```

用户已确认该 workbook 有外部数据源依赖，需要在上游 issue 中特别说明。

## 相关公式

`Sheet1!U1`：

```excel
=SUMPRODUCT(($A$4:$A$75=$S$4)*($B$4:$B$75=$U$3)*($C$3:$P$3=$T$4),$C$4:$P$75)
```

原始 `data_only=True` 关键值：

```text
U1 = 0
U4 = #VALUE!
U5 = 0
```

## import-only 复现

```bash
univer import data/spreadsheetbench_verified_400/spreadsheet/14240/1_14240_init.xlsx \
  .runs/tmp-import-only-check/14240.univer --json
univer pipe out .runs/tmp-import-only-check/14240.univer --range 'Sheet1!U1:U5' --format tsv
```

实际输出：

```text
#NAME?


#VALUE!
#NAME?
```

这与 Excel 期望的 `U1=0, U4=#VALUE!, U5=0` 不一致。另用 `univer run` 读取 `U75` 也为 `#NAME?`，Excel 中为 `0`。

扫描结果 `.runs/cli-roundtrip-ver400-abnormal-20260526-143009/results.csv` 也记录了同一问题：

```text
14240 input  Sheet1!U1  src=0  exported=#NAME?
14240 output Sheet1!U1  src=0  exported=#NAME?
```

分类为 `abnormal_formula_changed_at_value_cell`。

## 对 agent 失败的影响

历史 run 中 agent 写入 `U4:U75` 的 corrected `SUMPRODUCT` 公式后，日志自验公式模型匹配，但 `getCellDatas()` 中 `U4/U5/U75` 缓存值为 `#NAME?`，评测中 `U4:U75` 全部失败。最新 high run 改用 `INDEX/MATCH` 并已通过，因此该问题主要解释历史失败和 roundtrip 风险，不是最新 high run 的当前失败原因。

## 期望表现

在保留外部依赖限制的前提下，`univer import` 后的 workbook-visible state 应与 Excel 打开并重算后的结果一致。至少不应把 Excel 中为 `0` 的公式结果读成 `#NAME?`。

## 实际表现

import 后 `Sheet1!U1` 从 `0` 变为 `#NAME?`，`U5/U75` 也从 `0` 变为 `#NAME?`。

## 归因

这是 `univer-cli` / Univer 在外部依赖 workbook 场景下的公式导入或计算兼容性问题，不是 agent 题意理解错误。由于存在外部数据源依赖，建议上游排查时将其作为外部引用/依赖场景的 bug，而非普通本地公式计算 bug。

## 关联背景

该问题来自 SpreadsheetBench `spreadsheetbench_verified_400` task `14240`：

- 矩阵中历史多次 FAIL。
- 最新 high run 已通过，说明 agent 可绕过该公式路径。
- 本地 Excel 人工打开并手动计算后，原始 workbook 与期望结果一致。
