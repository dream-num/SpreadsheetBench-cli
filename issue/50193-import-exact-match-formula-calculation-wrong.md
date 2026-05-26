# 50193 import 后 EXACT/MATCH 公式链计算结果错误

## 摘要

`univer import` 导入 `spreadsheetbench_verified_400` task `50193` 后，`RS.Food` sheet 中依赖 `IFERROR(INDEX(...,MATCH(TRUE,EXACT(...),)),"")` 的公式链计算结果与 Excel/WPS 不一致。

原始 `1_50193_init.xlsx` 在 Excel 和 WPS 中打开并手动计算后，关键单元格仍显示：

```text
RS.Food!I8  = 空
RS.Food!J8  = 空
RS.Food!K8  = 空
RS.Food!I231 = Kids
RS.Food!J231 = 33
RS.Food!K231 = 1
```

但同一文件经 `univer import` 后，在 `.univer` 中读取到：

```text
RS.Food!I8  = Kids
RS.Food!J8  = 280
RS.Food!K8  = 4
RS.Food!I231 = Kids
RS.Food!J231 = 33
RS.Food!K231 = 58
```

上游 issue：`https://github.com/dream-num/univer-cli/issues/329`

## 最小复现

```bash
univer import data/spreadsheetbench_verified_400/spreadsheet/50193/1_50193_init.xlsx \
  .runs/tmp-import-only-check/50193.univer --json

univer run .runs/tmp-import-only-check/50193.univer --code '() => {
  const s = univerAPI.getActiveWorkbook().getSheetByName("RS.Food");
  return [8,231].map(r => ({
    row: r,
    I: s.getRange(`I${r}`).getValue(),
    J: s.getRange(`J${r}`).getValue(),
    K: s.getRange(`K${r}`).getValue()
  }));
}'
```

## 影响

该问题会让 agent 基于错误 workbook-visible state 做后续编辑和验证。50193 的任务要求修改 `RS.Food!K6:K607` 排名公式；由于导入后 `I/J/K` 公式链已经错误，agent 即使只修改 K 列，也会导出与 golden 不一致的结果。

在 `codex-gpt-5-5-high-verified400-wrong86-w8-20260526-150018` 中，output 与 golden 在 `RS.Food!K6:K607` 的 `data_only=True` 值有 `465/602` 个单元格不一致。

## 归因

这是 `univer-cli` / Univer 公式导入或计算兼容性问题，不是 Excel 缓存问题，也不是 agent 题意理解错误。
