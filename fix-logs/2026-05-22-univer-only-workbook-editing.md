# 限制 agent 只通过 univer-cli 修改 workbook

## 背景

在分析 Verified 400 的 `17-35` case 时发现，旧 prompt 虽然提供了预导入的 `/task/cases/case_1/input.univer`，但也说明原始 `.xlsx` 仍可作为 source reference。该表述在“保持原始格式”的题目中给 agent 留了绕过 `.univer` 编辑链路的空间。

旧运行中，agent 最终没有优先使用 `.univer -> univer run/pipe -> univer export`，而是转向直接读取和修改 `input.xlsx`：

- 先尝试 `python/openpyxl`，但容器内 `python` 和 `python3` 不存在。
- 再通过 `npm install exceljs@4` 安装运行时依赖。
- 用 ExcelJS 直接读写 `/task/cases/case_1/input.xlsx` 并生成 `output.xlsx`。
- 验证时还出现过 `univer import --overwrite` 参数错误。

虽然该 case 最终评测通过，但过程违反了希望稳定使用 `univer-cli` 的执行路径，也引入了 Python/Node/npm/外部库依赖风险。

## 修复内容

更新 `inference/univer_agent/prompts.py` 中的 agent 规则：

- 明确要求 workbook 读取、编辑、验证、导出只能使用已安装的 `univer` CLI 和 `univer-cli` skill 公共工作流。
- 将 `/task/cases/case_N/input.univer` 定义为解题时唯一 workbook source。
- 禁止用 Python、Node.js、npm packages、office libraries、zip tools 或任何非 `univer` workbook 工具读取、复制、导入、解析、检查或修改 `/task/cases/case_N/input.xlsx`。
- 要求最终 `.xlsx` 必须由编辑后的 `.univer` 通过 `univer export` 生成。
- 删除“原始 `.xlsx` 可作为 source reference”的旧表述。

同步更新 `tests/test_univer_agent_runner.py`，验证生成的 prompt 包含新约束，并不再包含旧的 source reference 口子。

## 验证

单测通过：

```text
python3 -m unittest tests.test_univer_agent_runner.UniverAgentRunnerTest.test_prepare_docker_task_workspace_copies_only_inputs_and_prompt
Ran 1 test in 0.013s
OK
```

重跑 `17-35` 单题：

```text
bash scripts/run_univer_agent_eval.sh --agent codex --env-file .env.codex --task-id 17-35 --run-id codex-gpt-5-5-verified400-task17-35-univeronly-20260522-1613
```

结果：

- task status: `ok`
- evaluation: `test_case_results: [1]`
- accuracy: `1.0`
- output: `I6:M294` 共 289 行，`I295:M295` 为空
- 最终通过 `univer export /task/cases/case_1/input.univer /task/outputs/case_1/output.xlsx` 生成输出

日志检查确认：

- 未执行 `npm install`
- 未执行 `python` / `python3`
- 未使用 `exceljs` / `openpyxl`
- 未直接读取或修改 `input.xlsx`
- 使用 `univer run` 修改 `.univer`
- 使用 `univer pipe out` 验证结果
- 使用 `univer export` 生成最终 `.xlsx`

## 时间对比

| 项目 | 旧 prompt | 新 prompt |
| --- | ---: | ---: |
| task | `17-35` | `17-35` |
| run-id | `codex-gpt-5-5-verified400-first80-20260522-033617` | `codex-gpt-5-5-verified400-task17-35-univeronly-20260522-1613` |
| summary 耗时 | `150.349s` | `127.834s` |
| Docker 内耗时 | `149.848s` | `127.513s` |
| 评测结果 | 通过 | 通过 |
| shell 命令数 | 18 | 20 |
| tokens | `44,934` | `47,200` |

新 prompt 虽然命令数和 token 略高，但去掉了 Python 失败重试、`npm install exceljs@4` 约 17 秒依赖安装、以及错误的 `--overwrite` 参数尝试，总耗时下降约 22.5 秒，执行路径也更稳定。
