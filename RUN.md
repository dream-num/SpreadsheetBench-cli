# 运行 Univer Agent 评测

当前主流程只有一条：

```text
外部 agent -> solution.js -> univer-cli replay -> evaluation report
```

所有命令都从项目根目录执行。

## 快速开始

用 Codex 跑一道题并自动评测：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --task-id 54513 --run-id codex-54513
```

用 Claude 跑一道题并自动评测：

```bash
bash scripts/run_univer_agent_eval.sh --agent claude --task-id 54513 --run-id claude-54513
```

使用自定义 agent：

```bash
bash scripts/run_univer_agent_eval.sh --agent-command 'my-agent --prompt-file "$SPREADSHEETBENCH_PROMPT_FILE" --out "$SPREADSHEETBENCH_SOLUTION_FILE"' --model my-agent --task-id 54513 --run-id my-agent-54513
```

一键脚本会依次执行：

```text
inference/replay -> evaluation
```

结束时会打印：

```text
Run summary: .runs/univer-agent/<run-id>/summary.json
Evaluation report: outputs/eval_<setting>_<model>.json
```

## 常用参数

指定 `data/` 下的测试集：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --dataset sample_data_200 --task-id 54513 --run-id codex-54513
```

只跑前 N 道题：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --limit 10 --run-id codex-first-10
```

只跑指定题目：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --task-id 54513 --task-id 59196 --run-id codex-two-tasks
```

覆盖输出目录里的 model 标签：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --model codex-exp1 --task-id 54513 --run-id codex-exp1-54513
```

最终输出会写到：

```text
data/<dataset>/outputs/univer_agent_<model>/
```

## Agent Preset

内置 agent preset：

```text
codex
claude
opencode
```

默认 model 标签：

```text
--agent codex          -> model label codex
--agent claude         -> model label claude，使用 stream-json verbose 输出，便于实时写日志
--agent opencode       -> 目前会提示不支持
自定义 agent            -> 使用 --agent-command，model label 默认为 agent，除非传 --model 或 MODEL
```

优先级规则：

```text
agent command: --agent-command > AGENT_COMMAND > --agent preset
model label:   --model > MODEL > preset model > agent
stream output: --stream-agent-output > STREAM_AGENT_OUTPUT=1
```

## 日志和结果在哪里看

最先看 run summary：

```text
.runs/univer-agent/<run-id>/summary.json
```

里面包含：

```text
metadata: dataset、setting、model、agent、cases、路径、开始/结束时间
tasks: 每道题的状态、workspace、solution 路径、output 路径、error
```

每道题都有一个 authoring 目录：

```text
.runs/univer-agent/<run-id>/<task-id>/authoring/
```

重要文件：

```text
prompt.md           实际给 agent 的完整提示词
agent.command.txt   实际执行的 agent 命令
agent.stdout.txt    agent 的完整 stdout
agent.stderr.txt    agent 的完整 stderr
agent.timing.json   agent 阶段开始/结束时间、耗时、return code、timeout
solution.js         agent 最终产出的可复用 Univer 脚本
input.xlsx          从 case 1 复制来的 authoring 输入
```

每个 replay case 都有自己的日志：

```text
.runs/univer-agent/<run-id>/<task-id>/case_1/univer.log
.runs/univer-agent/<run-id>/<task-id>/case_2/univer.log
.runs/univer-agent/<run-id>/<task-id>/case_3/univer.log
```

`univer.log` 会记录每一步 replay 命令：

```text
univer import input.xlsx workbook.univer
univer run workbook.univer --file <solution.js>
univer export workbook.univer output.xlsx
```

最终生成的 spreadsheet 输出：

```text
data/<dataset>/outputs/<setting>_<model>/<case>_<task-id>_output.xlsx
```

evaluation 报告：

```text
outputs/eval_<setting>_<model>.json
```

## Debug 顺序

先看总 summary：

```bash
cat .runs/univer-agent/<run-id>/summary.json
```

如果 agent 阶段失败，看：

```bash
cat .runs/univer-agent/<run-id>/<task-id>/authoring/agent.stderr.txt
cat .runs/univer-agent/<run-id>/<task-id>/authoring/agent.stdout.txt
cat .runs/univer-agent/<run-id>/<task-id>/authoring/agent.command.txt
```

如果 replay 阶段失败，看对应 case 的 `univer.log`：

```bash
cat .runs/univer-agent/<run-id>/<task-id>/case_1/univer.log
```

如果 evaluation 结果不对，看报告：

```bash
cat outputs/eval_<setting>_<model>.json
```

然后对照输出文件和标准答案文件中 `dataset.json` 声明的 `answer_position`：

```text
data/<dataset>/outputs/<setting>_<model>/<case>_<task-id>_output.xlsx
data/<dataset>/spreadsheet/<task-id>/<case>_<task-id>_answer.xlsx
```

## 测试没通过如何分析

如果 report 里某题没通过：

```json
"test_case_results": [1, 0, 1]
```

先看对应 run summary，确认输出文件路径：

```bash
cat .runs/univer-agent/<run-id>/summary.json
```

然后看失败 case 的 replay 日志：

```bash
cat .runs/univer-agent/<run-id>/<task-id>/case_2/univer.log
```

如果 replay 命令都是 `[exit 0]`，说明生成流程成功，但结果内容不匹配。继续检查：

```text
data/<dataset>/outputs/<setting>_<model>/2_<task-id>_output.xlsx
data/<dataset>/spreadsheet/<task-id>/2_<task-id>_answer.xlsx
```

重点对比 `dataset.json` 里的 `answer_position`。如果 case 1 通过但 case 2/3 失败，通常说明 agent 在 `solution.js` 里硬编码了 case 1 的值或范围，没有写成可复用逻辑。

## Agent 超时或耗时很长如何分析

agent 默认超时时间是 1800 秒，可以用参数调整：

```bash
bash scripts/run_univer_agent_eval.sh --agent claude --task-id 54513 --run-id claude-54513 --agent-timeout 3600
```

如果 agent 超时或被终止，先看：

```bash
cat .runs/univer-agent/<run-id>/<task-id>/authoring/agent.timing.json
cat .runs/univer-agent/<run-id>/<task-id>/authoring/agent.stderr.txt
tail -n 200 .runs/univer-agent/<run-id>/<task-id>/authoring/agent.stdout.txt
```

`agent.timing.json` 里有：

```text
started_at
finished_at
duration_seconds
returncode
timeout_seconds
```

如果 `agent.stdout.txt` 长时间没有增长，可能是：

```text
agent 本身不支持 streaming stdout
agent 卡在工具调用或外部命令
agent 等待权限确认
agent prompt 让它进行了过多探索
```

Claude preset 当前使用 `--output-format stream-json --verbose`，正常情况下 `agent.stdout.txt` 应该会持续增长。

如果整体执行时间很长，先看总耗时和每题耗时：

```bash
cat .runs/univer-agent/<run-id>/summary.json
```

每个 task 里有：

```text
started_at
finished_at
duration_seconds
```

再看 agent 阶段耗时：

```bash
cat .runs/univer-agent/<run-id>/<task-id>/authoring/agent.timing.json
```

如果 agent 阶段耗时很长，看最近的 agent 输出：

```bash
tail -n 200 .runs/univer-agent/<run-id>/<task-id>/authoring/agent.stdout.txt
```

重点判断 agent 是否在反复探索 workbook、反复验证同一个结果、等待外部命令、或生成了过长的思考/工具调用过程。

## 控制台输出

默认情况下，agent 的 stdout/stderr 会写入日志文件，但不会实时打印到终端。
如果所选 agent 支持 streaming stdout，日志文件会在 agent 运行过程中持续写入，可以用 `tail -f` 查看：

```bash
tail -f .runs/univer-agent/<run-id>/<task-id>/authoring/agent.stdout.txt
```

如果需要实时看 agent 输出：

```bash
STREAM_AGENT_OUTPUT=1 bash scripts/run_univer_agent_eval.sh --agent codex --task-id 54513 --run-id codex-54513-live
```

无论是否实时输出，下面两个文件都会写：

```text
agent.stdout.txt
agent.stderr.txt
```

## 只运行 Inference

如果只想生成输出，不跑 evaluation：

```bash
bash inference/scripts/inference_univer_agent.sh --agent codex --task-id 54513 --run-id codex-54513
```

## 只运行 Evaluation

如果输出已经存在，只想重新评测：

```bash
cd evaluation && ../.venv/bin/python evaluation.py --dataset sample_data_200 --setting univer_agent --model codex --task-id 54513
```

evaluation 会对选中的题固定检查 3 个 case。

## 不依赖真实 Agent 的 Smoke Test

这个命令用一个很小的 fake agent 写 `solution.js`，用于验证 runner、univer replay 和 evaluation 路径是否正常：

```bash
bash scripts/run_univer_agent_eval.sh --agent-command '/Users/otime/project/univer-cli-benckmark/SpreadsheetBench/.venv/bin/python -c "import os; open(os.environ[\"SPREADSHEETBENCH_SOLUTION_FILE\"], \"w\").write(\"() => {\\n  const workbook = univerAPI.getActiveWorkbook();\\n  const sheet = workbook.getSheetByName(\\\"Sheet1\\\");\\n  const price = parseFloat(String(sheet.getRange(\\\"C8\\\").getValue()).replace(/[$,]/g, \\\"\\\"));\\n  const discount = parseFloat(String(sheet.getRange(\\\"E8\\\").getValue()).replace(/%/g, \\\"\\\")) / 100;\\n  sheet.getRange(\\\"F8\\\").setValue(price * (1 - discount));\\n  return { success: true };\\n}\\n\")"' --model smoke --task-id 54513 --run-id smoke-54513
```

预期 evaluation report 里应该看到：

```json
"test_case_results": [1, 1, 1],
"soft_restriction": 1.0,
"hard_restriction": 1
```

## 常见问题

如果 `univer run` 报 daemon socket 相关错误，先看对应的 `univer.log`。
在当前机器上，`univer-cli` 有时需要访问本地 daemon socket 的权限。

如果一键脚本找不到 Python 包，显式指定项目虚拟环境：

```bash
PYTHON_BIN="$PWD/.venv/bin/python" bash scripts/run_univer_agent_eval.sh --agent codex --task-id 54513 --run-id codex-54513
```

如果 evaluation 报告里显示文件不存在，先确认 inference 已经为该任务生成 3 个 output workbook。
