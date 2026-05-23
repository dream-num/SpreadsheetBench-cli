# 13-1: pipe out / formula 输出缺少坐标导致 agent 误判行号

## 背景

- task-id: `13-1`
- run-id: `claude-deepseek-v4-flash-verified400-first80-20260522-233842`
- dataset: `spreadsheetbench_verified_400`
- agent: `claude`, model `DeepSeek-V4-Flash`
- instruction_type: `Sheet-Level Manipulation`
- answer_position: `A3:D32`
- runner 状态: `error`
- 失败原因: Docker 任务 300 秒超时
- 评测结果: `test_case_results: [0]`

题目要求从 `RANGES` sheet 汇总数据到 `LISTS` sheet，按 `DATE` 和 `REF` 去重合计，并在每个 section 末尾写入 `TOTAL`。

agent 实际已经完成主要数据处理，`DATA` 和 `OPERATION` section 的值、排序、合计结果都基本正确。但在最终导出前，agent 因验证公式范围时误判行号，继续调试直到 runner 超时，最终没有生成 `/task/outputs/case_1/output.xlsx`。

## 现象

agent 使用 `univer pipe out` 验证 `LISTS!A1:D32`：

```text
		STAGE	
SN	DATE	REF	AMOUNTS
1	2024-2-3	REAS	115.00
...
TOTAL			1,860.00
			
			
		DATA	
SN	DATE	REF	AMOUNTS
1	2024-2-22	REAS	1,545.00
...
TOTAL			4,755.00
			
			
		OPERATION	
SN	DATE	REF	AMOUNTS
1	2024-2-24	REAS	1,990.00
...
TOTAL			6,495.00
```

随后 agent 用 formula 输出检查：

```text
=SUM(D3:D9)


...
=SUM(D15:D19)
...
=SUM(D25:D31)
```

由于输出没有行号/坐标，空白分隔行又只表现为空白 tab 和换行，agent 靠肉眼数行后误判：

- 认为 `DATA` 数据行是 14-18，`TOTAL` 在 19。
- 认为 `OPERATION` 数据行是 23-29，`TOTAL` 在 30。
- 因此误以为 `=SUM(D15:D19)` 和 `=SUM(D25:D31)` 有偏移。

但后续 facade debug 已经证明真实位置是：

```json
{"type":"section","name":"DATA","row1":13}
{"type":"total","row1":20,"formulaD":"=SUM(D15:D19)"}
{"type":"section","name":"OPERATION","row1":23}
{"type":"total","row1":32,"formulaD":"=SUM(D25:D31)"}
```

也就是说，公式本身是对齐的；错误来自 agent 对裸文本输出的行号推断。

## 根因

当前 `pipe out` 默认输出是纯数据流，适合脚本消费，但对 agent 直接阅读不够友好：

1. `--format tsv` 不带 sheet 行号或 A1 坐标。
2. 空白行在日志中很难稳定计数，尤其是连续空行和 tab-only 行。
3. `--type formula` 输出同尺寸矩阵，但大部分单元格为空；没有坐标时，公式在哪一行只能靠数换行判断。
4. `inspect range` 虽然 preview 带 A1 坐标，但会省略中间行；formula groups 也可能把相似公式归组，只展示代表公式，不适合验证每个公式的实际坐标。
5. 0-based numeric API 与 1-based A1/formula 坐标是潜在认知负担，但本 case 中 agent 的代码换算原本是正确的，主要问题不是 index base 规则，而是输出展示缺少行号。

## 更可靠的验证方式

目前可以通过 `pipe out --format json` 结合 `jq` 自行加行号：

```bash
univer pipe out input.univer --range 'LISTS!A1:D32' --format json \
  | jq -r 'to_entries[] | "row \(.key+1):\t" + (.value | @tsv)'
```

公式定位可以用：

```bash
univer pipe out input.univer --range 'LISTS!A1:D32' --format json --type formula \
  | jq -r 'to_entries[] | .key as $i | .value | to_entries[] | select(.value != "") | "row \($i+1), col \(.key+1): \(.value)"'
```

得到的输出更适合 agent 判断：

```text
row 10, col 4: =SUM(D3:D9)
row 20, col 4: =SUM(D15:D19)
row 32, col 4: =SUM(D25:D31)
```

复杂结构边界也可以用 `univer run` facade API 输出结构化结果：

```javascript
() => {
  const wb = univerAPI.getActiveWorkbook();
  const sh = wb.getSheetByName("LISTS");
  const vals = sh.getRange("A1:D32").getValues();
  const formulas = sh.getRange("D1:D32").getFormulas();
  const sections = [];

  for (let i = 0; i < vals.length; i++) {
    const c = vals[i][2];
    const a = vals[i][0];
    if (c === "STAGE" || c === "DATA" || c === "OPERATION") {
      sections.push({ type: "section", name: c, row1: i + 1 });
    }
    if (String(a || "").toUpperCase() === "TOTAL") {
      sections.push({
        type: "total",
        row1: i + 1,
        formulaD: formulas[i]?.[0] || "",
        valueD: vals[i][3],
      });
    }
  }

  return { success: true, sections };
}
```

## 候选改进方向

### CLI 侧

- 给 `univer pipe out` 增加 agent 友好的坐标输出选项，例如：
  - `--row-numbers`
  - `--coordinates`
  - `--with-addresses`
- 对 `--type formula` 提供稀疏坐标输出模式，例如：

```text
LISTS!D10 = =SUM(D3:D9)
LISTS!D20 = =SUM(D15:D19)
LISTS!D32 = =SUM(D25:D31)
```

- 考虑给 `inspect range` 增加不省略行的坐标化 preview，或专门的 formula listing 输出。

### agent / skill 侧

- 在 `univer-cli` skill 或 benchmark prompt 中加入通用规则：
  - 涉及公式范围、section 边界、空白分隔行时，不要从裸 TSV 肉眼数行。
  - 优先使用 `pipe out --format json | jq ...` 加行号验证。
  - 公式验证优先使用 `pipe out --format json --type formula` 并转成坐标列表。
  - 复杂边界用 `univer run` 返回 `{ row1, formula, value }` 等结构化结果。
- 如果 workbook-visible 数据和合计已经验证正确，不要因裸文本行号疑似偏移继续无界调试；应优先导出，再在剩余时间做补充验证。

## 影响

- 对包含空白分隔行、多 section 表格、公式验证的任务，agent 容易被纯 TSV 输出误导。
- 误判会导致重复调试、错改本来正确的公式，或像本 case 一样耗尽 runner 超时时间。
- 这类问题不是具体题目特化问题，而是 CLI 输出格式与 LLM 阅读能力之间的不匹配。

## 风险

- 直接把所有验证命令写进 prompt 会增加 token，并可能让简单任务变慢；更适合放入 skill recipe 或 CLI 原生选项。
- `jq` 方案依赖容器环境有 `jq`；CLI 原生坐标输出会更稳定。
- `inspect range` 的 formula group 输出适合摘要，不应被 agent 当作逐公式坐标验证依据。
