# Agent 指令

- 当用户只说开始/运行测试且没有进一步说明时，按 `RUN.md` 的 SpreadsheetBench 流程执行。
- 启动命令：
  `bash scripts/run_univer_agent_eval.sh --agent <agent> --task-id <task-id> --run-id <run-id>`
- `run-id` 根据 agent、数据集、任务范围命名，并追加日期时间。
- 常用参数：`--agent`、`--agent-command`、`--model`、`--dataset`、`--task-id`、`--limit`、`--run-id`、`--agent-timeout`。详情见 `RUN.md`。
- 沙箱中运行 `codex`、`claude` 等外部 agent 时，如遇网络、认证、DNS、模型请求或依赖下载问题，按疑似沙箱限制处理，使用提权方式重跑测试命令。

## 数据集

- `sample_data_200`：样例数据集，200 道题；默认数据集。用户简写为 `sample`、`sample200`、`200` 或 `s200` 时，自动推断为该数据集。
- `all_data_912_v0.1`：完整数据集，912 道题。用户简写为 `all`、`full`、`912`、`all912` 或 `full912` 时，自动推断为该数据集。
- `spreadsheetbench_verified_400`：SpreadsheetBench Verified 数据集，400 道题。用户简写为 `verified`、`verify`、`v400`、`verified400` 或 `400` 时，自动推断为该数据集。

## 运行后分析

- 先看 `.runs/univer-agent/<run-id>/summary.json`：确认任务数、`ok/error/timeout`、耗时最高的任务。
- 再看 `report/<run-id>.json` 和 `outputs/eval_*<run-id>.json`：统计准确率、失败 case、超时 case。
- 对失败或超时 case，按以下顺序定位原因：
  1. 读该 case 的 `task/prompt.md`，确认 `answer_position` 和任务要求。
  2. 查 `task/logs/docker.output.txt`、`docker.stderr.txt`、`docker.timing.json`。
  3. 对比 output 与 golden 在 `answer_position` 内的差异；必要时同时检查值、公式、数字格式、样式、空白行和工作表结构。
  4. 判断失败类型：理解错误、范围/边界错误、值类型或格式错误、工具链错误、超时/网络问题。
- 对正确 case 也要扫日志中的可恢复问题，尤其是 `cp: omitting directory`、`Unknown argument`、`Missing workbook package file`、`Range is out of bounds`、`Sheet not found`、`python/jq not found`、`npm install`、`univer export` 崩溃等。报告中区分“最终正确但过程有问题”和“评测失败”。
- 用户要求详细分析时，输出两部分：失败/超时原因报告；正确 case 执行问题与优化建议。

# 语言
- 对话始终使用中文
