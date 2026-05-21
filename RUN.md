# 运行 Univer Agent 评测

当前主流程是 Docker-only 黑盒执行：

```text
host runner -> /task workspace -> Docker solver -> outputs/case_N/output.xlsx -> evaluation/report
```

host runner 不执行 workbook import、replay、export。为对标 main 分支的 SpreadsheetBench prompt 口径，host runner 会从 case 1 input workbook 读取前几行生成 `spreadsheet_content`，并把 dataset 中的 `answer_position` 放进 prompt。`solution.js` 或其他临时脚本只属于容器内部实现细节，外部 runner 不关心。

## 构建解题镜像

解题 Docker 环境放在独立目录：

```text
docker/spreadsheetbench-univer-cli-agent/
```

构建默认镜像：

```bash
bash scripts/build_agent_docker.sh
```

等价于：

```bash
docker build -t spreadsheetbench-univer-cli-agent docker/spreadsheetbench-univer-cli-agent
```

镜像内包含 Node/npm、bash、`univer-cli@latest`、Codex、Claude 和官方 `univer-cli` skill。基础系统包只保留脚本执行、拉取 npm/skill 所需的 bash、证书和 git。

## 认证

不要把 Codex/Claude 认证写进镜像，也不要复制进 task 目录。推荐使用 env 文件：

```dotenv
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
```

默认 env-file 规则：

- 如果命令行传了 `--env-file <path>`，使用该文件。
- 如果没有显式传 `--env-file`，且仓库根目录存在 `.env.agent`，inference 脚本会自动使用 `.env.agent`。
- runner 只把 env 文件路径传给 `docker run --env-file`，不会把 env 文件复制到 `/task`，也不会记录文件内容。

不同 agent 的推荐 env-file：

- `--agent codex`：优先显式使用 `.env.codex`。
- `--agent claude`：优先显式使用 `.env.claude`。
- 自定义 `--agent-command`：按该命令需要显式传对应 env 文件。

Claude 推荐优先使用仓库根目录的 `.env.claude`：

```bash
bash scripts/run_univer_agent_eval.sh \
  --agent claude \
  --env-file .env.claude \
  --task-id 54513
```

Codex 推荐优先使用仓库根目录的 `.env.codex`：

```bash
bash scripts/run_univer_agent_eval.sh \
  --agent codex \
  --env-file .env.codex \
  --task-id 54513
```

`.env.codex` 会按本机 Codex 配置设置模型和代理，并通过 `CODEX_AUTH_JSON` 把本机 `~/.codex/auth.json` 只读挂载到容器内的 `CODEX_HOME/auth.json`。这样可以复用本机 ChatGPT 登录态，但不会把认证文件复制进镜像或 task workspace。容器内已经由 Docker 隔离，`.env.codex` 默认设置 `CODEX_BYPASS_SANDBOX=1`，避免 Codex CLI 在容器里再次启用 bubblewrap sandbox 导致命令无法运行。

## 快速开始

默认数据集是 `spreadsheetbench_verified_400`。未显式传 `--run-id` 时，脚本会自动生成：

```text
<agent>-<dataset>-<scope>-YYYYMMDD-HHMMSS
```

例如：

```text
codex-verified400-first50-20260521-143000
```

用 Codex 跑一道题并自动评测：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --env-file .env.codex --task-id 54513
```

用 Claude 跑一道题并自动评测：

```bash
bash scripts/run_univer_agent_eval.sh --agent claude --env-file .env.claude --task-id 54513
```

使用自定义容器内命令：

```bash
bash scripts/run_univer_agent_eval.sh \
  --agent-command 'my-agent --prompt-file "$SPREADSHEETBENCH_PROMPT_FILE"' \
  --model my-agent \
  --task-id 54513
```

## 常用参数

指定数据集：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --env-file .env.codex --dataset sample_data_200 --task-id 54513
```

只跑前 N 道题：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --env-file .env.codex --limit 10
```

只跑指定题目：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --env-file .env.codex --task-id 54513 --task-id 59196
```

控制 task 级并发数，默认是 5：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --env-file .env.codex --limit 10 --workers 3
```

指定 Docker 命令：

```bash
bash scripts/run_univer_agent_eval.sh \
  --agent codex \
  --env-file .env.codex \
  --docker-bin docker \
  --task-id 54513
```

覆盖输出目录里的 model 标签：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --env-file .env.codex --model codex-exp1 --task-id 54513
```

最终输出会写到：

```text
data/<dataset>/outputs/univer_agent_<model>/
```

## Task Workspace

host runner 为每个 task 创建独立目录：

```text
.runs/univer-agent/<run-id>/<task-id>/task/
  prompt.md
  cases/
    case_1/input.xlsx
    case_2/input.xlsx
  outputs/
    case_1/
    case_2/
  logs/
  work/
```

Docker 只挂载当前 task 目录：

```bash
docker run --rm \
  --name spreadsheetbench-cli-<run-id>-<task-id> \
  --env-file /abs/path/.env.agent \
  -v /abs/path/.runs/univer-agent/<run-id>/<task-id>/task:/task \
  spreadsheetbench-univer-cli-agent \
  --agent codex
```

容器必须写出：

```text
/task/outputs/case_1/output.xlsx
/task/outputs/case_2/output.xlsx
```

host runner 检查这些文件，并复制到 benchmark 标准输出路径：

```text
data/<dataset>/outputs/<setting>_<model>/<case>_<task-id>_output.xlsx
```

## 隔离和 Prompt 信息

当前 prompt 对标 main 分支，会提供：

```text
instruction
spreadsheet_path
spreadsheet_content
instruction_type
answer_position
output_path
```

`spreadsheet_content` 来自 case 1 input workbook 的前 5 行。host runner 不会生成 `workbook_context.md`，也不会挂载 answer 文件。

容器不能访问 answer 文件、dataset 根目录、其他 task workspace 或 report。agent 可以在容器内自行使用 `univer inspect/search/pipe/run/help` 或读取当前 task 的 `input.xlsx`。

## 日志和结果

最先看 run summary：

```text
.runs/univer-agent/<run-id>/summary.json
```

每个 task 的 Docker 日志在：

```text
.runs/univer-agent/<run-id>/<task-id>/task/logs/docker.command.txt
.runs/univer-agent/<run-id>/<task-id>/task/logs/docker.stdout.txt
.runs/univer-agent/<run-id>/<task-id>/task/logs/docker.stderr.txt
.runs/univer-agent/<run-id>/<task-id>/task/logs/docker.output.txt
.runs/univer-agent/<run-id>/<task-id>/task/logs/docker.timing.json
```

evaluation 报告：

```text
outputs/eval_<setting>_<model>.json
outputs/eval_<setting>_<model>_<run-id>.json
```

统一报告：

```text
report/<run-id>.json
```

## Debug 顺序

先看总 summary：

```bash
cat .runs/univer-agent/<run-id>/summary.json
```

如果 Docker 阶段失败：

```bash
cat .runs/univer-agent/<run-id>/<task-id>/task/logs/docker.stderr.txt
cat .runs/univer-agent/<run-id>/<task-id>/task/logs/docker.stdout.txt
cat .runs/univer-agent/<run-id>/<task-id>/task/logs/docker.command.txt
```

如果 Docker 成功但任务失败，通常是缺少某个输出：

```bash
find .runs/univer-agent/<run-id>/<task-id>/task/outputs -maxdepth 3 -type f
```

如果 evaluation 不通过，看报告和标准输出文件：

```text
outputs/eval_<setting>_<model>_<run-id>.json
data/<dataset>/outputs/<setting>_<model>/<case>_<task-id>_output.xlsx
```

answer 文件只用于人工离线排查，不会挂载进 Docker 容器。
