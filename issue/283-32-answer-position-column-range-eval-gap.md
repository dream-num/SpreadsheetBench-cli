# 283-32: answer_position 使用整列范围导致评测器解析失败

## 背景

- task-id: `283-32`
- run-id: `codex-gpt-5-5-verified400-first80-20260523-163607`
- dataset: `spreadsheetbench_verified_400`
- agent: `codex`, model `gpt-5.5`
- instruction_type: `Sheet-Level Manipulation`
- answer_position: `Sheet3'!A:G,'Sheet4'!A:G`
- runner 状态: `ok`
- 评测结果: `test_case_results: [0]`
- 耗时: `106.613s`

题目要求比较 `Sheet1` 和 `Sheet2` 两个快照，将 `Sheet1` 有但 `Sheet2` 没有的内部数据写到 `Sheet3`，将 `Sheet2` 新增的内部数据写到 `Sheet4`，不需要表头，从第 1 行开始输出。

## 现象

当前 agent 最终输出值与 golden 一致：

```text
Sheet3!A1:G1 = 2022-02-01, Dr, C, Sales, 042, blank, 908010
Sheet4!A1:G1 = 2022-02-01, Dr, I, Sales, 048, blank, 1000
```

用 `openpyxl` 对 output 和 golden 的 `Sheet3/Sheet4 A:G` 做值对比，结果为：

```text
--- diff Sheet3
count 0
--- diff Sheet4
count 0
```

但评测结果仍为 0。

直接调用当前评测函数复现，会抛出：

```text
ValueError: invalid literal for int() with base 10: ''
```

## 根因

当前 `evaluation/evaluation.py` 的 `parse_cell_range()` 只支持带行号的范围，例如：

```text
A1:G2
```

但本题 `answer_position` 是整列范围：

```text
Sheet3'!A:G,'Sheet4'!A:G
```

解析 `A:G` 时，起止行号都是空字符串，评测器执行 `int('')` 抛错。主评测循环捕获异常后将该 case 记为失败。

因此这是题目标注与评测程序能力不匹配：

1. 题目/数据侧给出了合法但更宽泛的整列范围 `A:G`。
2. 评测器侧只实现了 `A1:G2` 这类显式行号范围。
3. agent 输出值正确，但评测器无法解析 `answer_position`，导致误判失败。

## agent 过程问题

agent 过程里有一次命令误用：

```text
univer export ... --overwrite
Unknown argument: overwrite
```

随后 agent 用 `rm -f output.xlsx && univer export ... --json` 恢复成功，最终生成了正确 output。这不是本 case 评测失败的直接原因。

agent 的实现方式也不是完全通用：它通过读取 Sheet1/Sheet2 后硬编码写入识别出的两条差异行，而不是保留一个通用比较脚本。但最终值与 golden 一致。

## 候选处理方向

### 短期分析口径

在继续逐题分析当前 `codex-gpt-5-5-verified400-first80-20260523-163607` 失败 case 时，跳过 `283-32`，不要将其归因于 agent 或 `univer-cli` 输出错误。

### 评测程序候选修复

如果后续要修评测器，可支持整列范围：

```text
A:G -> A1:G<max_row>
```

其中 `max_row` 应取 golden sheet 和 output sheet 的较大使用行：

```text
max(ws_gt.max_row, ws_proc.max_row)
```

这样既能比较 golden 中应有的行，也能发现 output 多写的额外行。

修复时应补测试：

- `A1:G2` 原有范围格式仍正常。
- `A:G` 能比较到两个 workbook 的最大使用行。
- output 多写额外行时应失败。
- 空白值 `None` / `""` 仍沿用现有等价逻辑。

## 风险

- 如果不修评测器，这类整列 `answer_position` 会持续被误判为失败。
- 如果直接把 `A:G` 展开到 Excel 最大行，会有性能风险；应只展开到实际使用行。
- 如果只展开到 golden 最大行，可能漏掉 output 范围内额外污染；因此候选修复应使用 golden/output 的较大 `max_row`。
