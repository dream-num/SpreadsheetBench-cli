# Univer `getDisplayValue(s)` is not final display text

## 背景

在 task `48969` 的 prompt 实验中，agent 写入 boolean cell model 后使用 `getDisplayValues()` 复查，看到 `1` / `0`，误以为最终显示文本不是 `TRUE` / `FALSE`，随后把结果改成字符串 `"TRUE"` / `"FALSE"`，导致评测失败。

## 复现

最小复现 workbook：`/private/tmp/univer-bool-display-20260530.univer`

写入：

```ts
sheet.getRange("A1:B1").setValues([[{ v: 1, t: 3 }, { v: 0, t: 3 }]]);
sheet.getRange("A3:B3").setValues([[{ f: "=TRUE()" }, { f: "=FALSE()" }]]);
await univerAPI.getFormula().onCalculationResultApplied();
```

读取结果：

```json
{
  "A1:B1": {
    "display": [["1", "0"]],
    "cellDatas": [[{ "v": 1, "t": 3 }, { "v": 0, "t": 3 }]]
  },
  "A3:B3": {
    "display": [["1", "0"]],
    "cellDatas": [[{ "f": "=TRUE()", "v": 1, "t": 3 }, { "f": "=FALSE()", "v": 0, "t": 3 }]]
  }
}
```

导出为 xlsx 后，`openpyxl.load_workbook(..., data_only=True)` 读取为标准 boolean：

```text
A1=True  data_type='b'
B1=False data_type='b'
A3=True  data_type='b'
B3=False data_type='b'
```

## 根因线索

当前 `@univerjs/sheets` facade 的 `FRange.getDisplayValue()` / `getDisplayValues()` 只是对 `cell.v` 做 `toString()`，没有调用 core 中已有的 `getDisplayValueFromCell(cell)`。

已确认代码位置：

- `@univerjs/sheets/lib/es/facade.js`: `getDisplayValue()` / `getDisplayValues()` 返回 `cell.v.toString()`
- `@univerjs/core/lib/es/index.js`: `getDisplayValueFromCell(cell)` 对 `cell.t === BOOLEAN` 会把 numeric payload `1/0` 转为 `TRUE/FALSE`
- `@univerjs/sheets-numfmt/lib/es/index.js`: number format cell content interceptor 对 `CellValueType.BOOLEAN` 直接跳过

## 影响

`getDisplayValue(s)` 当前不能当作最终 spreadsheet / Excel 显示文本使用。对 boolean cells，API 返回 `1` / `0`，但导出的 Excel 语义是 `TRUE` / `FALSE`。

## 当前规避

agent prompt 已补充：`getDisplayValue()` / `getDisplayValues()` 不是最终 spreadsheet 或 Excel display text。boolean 类型应以 `getCellDatas()` 的 `t: 3` 和 `v: 1/0` 为准。

## 候选修复方向

在 Univer facade 层让 `getDisplayValue()` / `getDisplayValues()` 复用 core 的 `getDisplayValueFromCell(cell)`，至少覆盖 boolean cell model。
