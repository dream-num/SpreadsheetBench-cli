# 333-29: active sheet 设置 API 未写入 help/skill 导致 agent 探测超时

## 背景

- task-id: `333-29`
- run-id: `codex-gpt-5-5-verified400-first80-20260522-233927`
- dataset: `spreadsheetbench_verified_400`
- agent: `codex`, model `gpt-5.5`
- instruction_type: `Sheet-Level Manipulation`
- answer_position: `B'!F4`
- runner 状态: `timeout`
- timeout: Docker command timed out after 300 seconds

题面要求把结果写入 `B!F4`，同时要求流程结束时 `A` sheet 为 active sheet：

```text
The 'A' sheet should be active when the process ends.
```

agent 已经正确写入并验证了 `B!F4`，但因为 `univer help run` 和 skill 中没有记录 active sheet 设置方法，它持续尝试通过 sheet 创建顺序、重命名顺序和导出后再导入验证来推断 active sheet 行为，最终 300 秒超时。

## 现象

agent 在 workbook 中已经正确写入：

```text
B!F4 = 5-Feb-14
```

手动只比较 `answer_position`：

```text
compare_workbooks(..., "B'!F4") -> (True, "")
Cell values in the specified range are identical.
```

但 runner 层面判为 timeout，因为 agent 没有在 300 秒内退出。

## 文档缺口

`FWorkbook` facade 实际有 active sheet 设置 API：

```javascript
const fWorkbook = univerAPI.getActiveWorkbook();

// 方式 1：传 FWorksheet
const sheet = fWorkbook.getSheets()[1];
fWorkbook.setActiveSheet(sheet);

// 方式 2：传 sheetId
fWorkbook.setActiveSheet("sheet-id");
```

对应方法：

```typescript
setActiveSheet(sheet: FWorksheet | string): FWorksheet
```

但当前 `univer-cli` skill 和 `univer help run` 文档没有记录该 API：

- `univer help run core`
  - 有 `univerAPI.getActiveWorkbook()`
  - 有 `getSheetByName()`、`getSheets()`、`create()`、`deleteSheet()`
  - 有 `setName()`、行列操作、`getRange()` 等
  - 没有 `setActiveSheet` / `activate` / `selectSheet`
- `univer help run sheets`
  - 有 sheet 创建、删除、重命名、冻结、网格线、行列展示等
  - 没有设置 active sheet 的方法
- `univer-cli` skill 也没有说明 active sheet 可通过 `FWorkbook.setActiveSheet(...)` 设置

因此 agent 面对 active sheet 要求时只能猜测或探测：

- 通过 sheet 创建顺序影响 active sheet
- 通过重命名 `Sheet1` 为 `A` / `B` 间接控制 active sheet
- 导出后再 import 回 `.univer` 检查 active sheet
- 反复覆盖 `output.xlsx` 并重新验证

这些探测不是核心单元格编辑，但消耗了大量时间并最终导致 timeout。

## 复现要求

给 `univer-cli` 报 issue 时，复现环境和步骤应该独立于 SpreadsheetBench：

- 只依赖 `univer-cli`
- 使用 issue 中附带的最小复现文件或 issue body 中的最小脚本
- 手动执行步骤即可看到：目前 help/skill 文档中找不到 `FWorkbook.setActiveSheet(...)`，agent 难以按文档化方式设置 active sheet

## 候选改进方向

请在 `univer help run core` 或 `univer help run sheets` 明确记录 `FWorkbook.setActiveSheet(...)`：

- API 名称
- 参数
- 示例
- 是否影响 `univer export` 后 `.xlsx` 打开时的 active sheet
- 如何用 `univer inspect workbook` 或其它命令验证

## 风险

- 如果没有明确 API 或明确不支持说明，agent 会继续猜测内部或间接行为。
- 这类问题会在题面包含 “active sheet / selected sheet / current sheet / focus” 要求时复现。
- 即使目标 cell/range 已经正确，也可能因为 UI 状态探测而超时。
