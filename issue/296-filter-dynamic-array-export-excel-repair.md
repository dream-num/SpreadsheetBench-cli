# Issue 296: FILTER 动态数组导出后被 Excel 修复并删除公式

## GitHub issue

- URL: https://github.com/dream-num/univer-cli/issues/296
- 标题：`bug: 含 FILTER 动态数组公式的导出 xlsx 会被 Excel 修复并删除公式`
- 目标仓库：`dream-num/univer-cli`

## 问题描述

使用 `univer new` 创建 workbook，通过 `univer run` 写入普通公式和 `FILTER` 动态数组公式后，Univer 内部可见状态能正确计算并显示 spill 结果；但执行 `univer export` 导出的 `.xlsx` 无法被 Microsoft Excel 正常打开。

Excel 打开导出的文件时会弹出修复提示。确认修复后，`FILTER` 公式会被删除。同时，导出的 `.xlsx` 也没有保留公式起点之后的 spill 缓存值。

## 最小复现

```bash
mkdir -p repro
univer new repro/repro.univer --name Repro
```

创建 `repro/setup.js`：

```js
async () => {
  const workbook = univerAPI.getActiveWorkbook();
  const sheet = workbook.getActiveSheet();

  sheet.getRange('A1:A2').setValues([[1], [2]]);
  sheet.getRange('B1').setFormula('=SUM(A1:A2)');

  sheet.getRange('D1:E4').setValues([
    ['source', 'keep'],
    [1, 'yes'],
    [2, 'no'],
    [3, 'yes'],
  ]);

  sheet.getRange('G1').setFormula('=FILTER(D2:D4,E2:E4="yes")');

  await univerAPI.getFormula().onCalculationResultApplied();

  return {
    success: true,
    values: sheet.getRange('A1:H5').getValues(),
    formulas: sheet.getRange('A1:H5').getFormulas(),
  };
}
```

执行：

```bash
univer run repro/repro.univer --file repro/setup.js
univer pipe out repro/repro.univer --range 'Sheet1!A1:H5' --format tsv
univer export repro/repro.univer repro/export.xlsx
```

Univer 内部可见状态正确：

```text
B1 = 3
G1 = 1
G2 = 3
```

导出后用 `openpyxl(data_only=True)` 读取：

```text
B1 = 3
G1 = 1
G2 = None
```

导出的 worksheet XML 中只有 `G1` 的裸 `FILTER` 公式：

```xml
<c r="G1" s="1">
  <f>FILTER(D2:D4,E2:E4="yes")</f>
  <v>1</v>
</c>
```

## Excel 打开表现

使用 Microsoft Excel 打开 `repro/export.xlsx` 时，Excel 会弹出修复提示。确认修复后，`FILTER` 公式会被删除。

因此问题不只是缓存值缺失；导出的 `.xlsx` 对 Excel 来说不是一个兼容的动态数组公式文件。

## SpreadsheetBench 关联背景

该问题是在 SpreadsheetBench Verified 400 的 Codex 全量运行中发现的。

- run-id: `codex-gpt-5-5-verified400-all-20260523-230050`
- dataset: `spreadsheetbench_verified_400`
- 本地分析目录：`analaysix/codex-gpt-5-5-verified400-all-20260523-230050/`

和动态数组 / `FILTER` / spill 导出相关的题目包括：

- `220-7665`: 动态数组只写入起点，导出后后续 spill 区域为空。
- `323-54085`: `FILTER` 在 Univer 内部状态正确，但导出 XLSX 未保留完整 spill/cache。
- `340-56378`: 动态 `FILTER` spill 导出后未完整保留。
- `387-58499`: `.univer` 中 `FILTER` spill 正确，导出后后续 spill 单元格丢失。

另外还有部分相关现象：

- `328-54667`: Univer 内可见公式计算结果，但导出后多行公式缓存缺失。
- `399-59884`: 依赖已有 dynamic array / spill 区域时，Univer 可见结果和导出 / golden 缓存行对齐不一致。

这些 SpreadsheetBench case 不是该 issue 的最小复现依赖；上面的 `repro/` 命令已可独立复现导出文件被 Excel 修复并删除 `FILTER` 公式的问题。

## 复验更新：`130-33722` 不再按本 issue 归类

2026-05-25 使用当前镜像单题重跑：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --dataset spreadsheetbench_verified_400 --task-id 33722 --run-id tmp-codex-verified400-task33722-export-timeout-20260525-verify --agent-timeout 300
```

结果：

- runner status: `ok`
- accuracy: `1.0`
- total/correct/error/timeout: `1/1/0/0`
- evaluation: `Cell values in the specified range are identical.`
- 新 run 中 `univer export` 在约 0.5 秒内完成。

旧基线 `codex-gpt-5-5-verified400-all-20260523-230050` 中 `33722` 的 300 秒超时没有在当前镜像/当前 agent 输出下复现，因此后续不再把 `33722` 作为本动态数组导出 issue 的关联失败处理。
