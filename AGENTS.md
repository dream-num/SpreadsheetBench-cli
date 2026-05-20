# Agent 指令

- 在本仓库中，当用户只说开始/运行测试而没有进一步说明时，将其视为 `RUN.md` 中记录的 SpreadsheetBench 运行流程。
- 使用以下命令启动测试：
  `bash scripts/run_univer_agent_eval.sh --agent <agent> --task-id <task-id> --run-id <run-id>`
- 在沙箱环境中运行 `codex`、`claude` 等外部 agent 时，agent 进程可能因为沙箱网络限制而无法连接服务端或下载依赖。若出现网络连接、认证、DNS、模型请求失败等疑似沙箱导致的问题，需要使用提权方式重新运行测试命令。
- 常见的可配置选项包括 `--agent`、`--agent-command`、`--model`、`--dataset`、`--task-id`、`--limit`、`--run-id` 和 `--agent-timeout`。详情和示例见 `RUN.md`。
- 当前可用数据集如下：
  - `sample_data_200`：样例数据集，200 道题；默认数据集。用户简写为 `sample`、`sample200`、`200` 或 `s200` 时，自动推断为该数据集。
  - `all_data_912_v0.1`：完整数据集，912 道题。用户简写为 `all`、`full`、`912`、`all912` 或 `full912` 时，自动推断为该数据集。
  - `spreadsheetbench_verified_400`：SpreadsheetBench Verified 数据集，400 道题。用户简写为 `verified`、`verify`、`v400`、`verified400` 或 `400` 时，自动推断为该数据集。
- 测试程序结束后，根据用户要求的详细程度，分析运行摘要、日志、生成的输出以及评测报告。
