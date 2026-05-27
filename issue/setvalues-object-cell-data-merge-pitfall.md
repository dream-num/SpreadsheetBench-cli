# setValues 对象 CellData 合并语义导致旧内容残留

## 问题

`setValues()` 写入对象形式的 `ICellData` 时不是“整格替换”，而是把传入对象合并到已有单元格。传入 `{}` 或仅包含样式的对象（例如 `{ s: ... }`）不会清除旧的值、公式、富文本或 custom 数据。

这会影响删除、筛选、排序、压缩、重排行等“把转换后的行写回原 answer range”的任务：如果输出行中的空白位置用 `{}` 或 style-only cell 表示，目标区域旧内容可能残留，最终 `openpyxl(data_only=True)` 评测仍能读到旧值。

## 触发样例

- Dataset: `spreadsheetbench_verified_400`
- Task: `23-24`
- Baseline run: `codex-gpt-5-5-verified400-all-20260526-231834`
- Baseline result: `test_case_results=[0]`
- answer_position: `Sheet1!A1:E1102`

baseline agent 删除 column A 命中 column I 的行后，把剩余行写回 `A1:E1102`。尾部和部分空白列使用 `{}` 或只保留样式对象，导致 B/C/D/E 旧值残留。

## 源码确认

本地 `/Users/otime/project/univer` 源码显示：

- `packages/sheets/src/facade/f-range.ts`: `FRange.setValues()` 调用 `covertCellValues()` 后执行 `SetRangeValuesCommand`。
- `packages/core/src/shared/common.ts`: `covertCellValues()` 对二维数组按目标 range 逐格转换。
- `packages/sheets/src/commands/mutations/set-range-values.mutation.ts`: `SetRangeValuesMutation` 对 falsy 新值执行 `realDeleteValue()`；对对象新值执行 `mergeCellData(newVal, oldVal, styles)`。
- `mergeCellData()` 只更新传入对象中存在的字段；缺失的 `v/f/p/si/custom` 不会自动清除旧内容。
- `clearContent()` 内部生成 `{ v: null, p: null, f: null, si: null, custom: null }` 这类 null content fields 来清内容并保留格式。

## 通用处理方式

替换整个范围时：

```js
targetRange.clearContent();
targetRange.setValues(rectangularValues);
```

如果只想通过 `setValues()` 清空个别单元格内容，应显式写 null content fields：

```js
{ v: null, f: null, p: null, si: null, custom: null }
```

不要把 `{}` 或 `{ s: ... }` 当作清空单元格内容。

## 已实施改进

已在 `inference/univer_agent/prompts.py` 增加通用提示词，说明 `setValues()` 的 merge 行为、`{}` / style-only object 的坑点、替换范围前应先 `clearContent()`，以及通过 `setValues()` 清空个别单元格时应写 explicit null content fields。

验证记录见：

- `fix-logs/2026-05-27-setvalues-merge-clearcontent-prompt.md`
