# 54590 外部引用公式缓存污染导致 GK29 评测失败

## 摘要

SpreadsheetBench Verified 400 task `54590` 最新两次 codex gpt-5.5 报告仍为 `FAIL`，但最新失败形态已经不是 `issue#317` 的条件格式 `notContainsText` 非法 operator 导致 `openpyxl` 无法读取。

最新 `allwrong96-exskip-w5-timeout480-20260527-232251` 中，output 和 golden 都可以被 `openpyxl.load_workbook(..., data_only=True)` 读取。正式评测失败的直接原因是 `answer_position=GK29` 的缓存值不同：

```text
golden HR !GK29 data_only = 692.71486185
output HR !GK29 data_only = 0
```

## 关联 run

```text
run-id: codex-gpt-5-5-verified400-allwrong96-exskip-w5-timeout480-20260527-232251
task-id: 54590
answer_position: GK29
```

## 题目要求

用户要求在 `GK29` 创建公式，基于 `GO` 列为 `yes` 计算 `GK` 与 `GR` 两列的和。原公式为：

```excel
SUMIFS(GK3:GK21,GK3:GK21,"<>#N/A",$GO$3:$GO$21,"yes")+SUMIFS(GR3:GR21,GR3:GR21,"Yes")
```

golden 的 `GK29` 公式为：

```excel
=SUMIFS(GK3:GK21,GK3:GK21,">0",$GO$3:$GO$21,"yes")+_xlfn.AGGREGATE(9,6,GR3:GR21)
```

## 关键证据

原始 `init.xlsx` 和 golden 中，`GK3:GK20` 是外部 workbook 引用公式：

```excel
=INDEX('[1]May 2021'!$L$2:$L$29,MATCH('HR '!$A3,'[1]May 2021'!$A$2:$A$29,0))
```

Excel/openpyxl 读取原始缓存时，`GK3:GK20` 和 `GO3:GO20` 有可用于计算的缓存值。按 `GO=yes` 手工汇总，目标值为：

```text
sum(GK rows where GO=yes) + valid GR values = 692.71486185
```

但导入到 Univer 后，agent 日志中的 workbook-visible 状态已经显示大量源公式缓存变成 `#N/A`：

```text
GK3:GK21 -> mostly #N/A
GO3:GO21 -> mostly #N/A, only GO13 remains Yes
GR8 -> #N/A
GK29 before edit -> #N/A
```

agent 因此写入了一个基于当前 Univer 可见状态的容错公式：

```excel
=SUMPRODUCT((IFERROR($GO$3:$GO$21,"")="yes")*IFERROR(GK3:GK21,0))+SUMPRODUCT((IFERROR($GO$3:$GO$21,"")="yes")*IFERROR(GR3:GR21,0))
```

该公式在被污染的 Univer 计算状态下导出缓存为 `0`，正式评测只读取 `data_only=True` 缓存值，因此失败。

## 对照实验

在同一导入后的 `.univer` 临时副本中直接写入 golden 公式：

```excel
=SUMIFS(GK3:GK21,GK3:GK21,">0",$GO$3:$GO$21,"yes")+AGGREGATE(9,6,GR3:GR21)
```

Univer 仍计算为：

```text
GK29 rawValue = 0
导出后 openpyxl data_only GK29 = 0
导出后 GK3/GO3/GR8 缓存仍为 #N/A
```

这说明仅替换成 golden 公式不能修复当前评测失败；根因在导入/计算阶段的外部引用公式缓存已经被污染。

## 归因

主要归因是 `univer-cli` / Univer 对外部 workbook 引用公式的导入或计算兼容性问题：导入后 workbook-visible 源公式缓存从 Excel 原有缓存值变成 `#N/A`，进而导致目标公式缓存值错误。

agent 也存在策略问题：它根据被污染的 Univer 可见状态推导公式并验证为 `0`，没有意识到源数据缓存与 Excel/golden 缓存不一致。但在 runner 约束下，agent 不能直接读取原始 `.xlsx` 或 golden，因此很难仅靠当前 prompt 从被污染状态恢复正确数值。

## 与 issue#317 的关系

`issue#317` 描述的是条件格式 `notContainsText` 被导出为非法 `operator="notContainsText"`，导致 `openpyxl` 读取失败。

最新 `54590` 输出中，`openpyxl` 可读取 output/golden；worksheet XML 中仍有 `type="notContainsText"`，但没有非法 `operator="notContainsText"`。因此最新失败不应继续归因为 issue#317。

## 后续方向

- 上游层面：调查外部 workbook 引用公式导入后缓存变为 `#N/A` 的问题，类似 `issue/14240-external-formula-roundtrip-name-error.md` 中的外部依赖公式缓存/兼容性问题。
- runner/agent 层面：对含外部 workbook 引用的任务，提示 agent 不要完全信任导入后的公式缓存；但在禁止读取原始 `.xlsx` 的约束下，通用恢复空间有限。
- 矩阵备注应将 `54590` 从纯 `issue#317` 迁移为“最新失败为外部引用公式缓存污染；issue#317 非当前失败形态”。
