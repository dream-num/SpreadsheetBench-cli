# 运行 Univer Agent 评测

当前主流程是 Docker-only 黑盒执行：

```text
host runner -> /task workspace -> Docker solver -> outputs/case_N/output.xlsx -> evaluation/report
```

host runner 只负责准备 `/task`、通过 Docker solver image 内的 `univer import` 把 `input.xlsx` 预导入为 `input.univer`、收集输出和执行评测；解题、修改 workbook、导出 `output.xlsx` 都在 Docker solver 内完成。为对标 main 分支的 SpreadsheetBench prompt 口径，host runner 会从 case 1 input workbook 读取前几行生成 `spreadsheet_content`，并把 dataset 中的 `answer_position` 放进 prompt。`solution.js` 或其他临时脚本只属于容器内部实现细节，外部 runner 不关心。

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

不要把 Codex/Claude 认证写进镜像，也不要复制进 task 目录。`.env.<agent>` 只保存本地配置文件路径，真实认证放在 agent 原生配置文件中，并由 runner 只读挂载到容器固定位置。

默认配置文件：

- `.env.codex`：
  ```dotenv
  CODEX_AUTH_JSON=codex-auth.json
  CODEX_CONFIG_TOML=codex-config.toml
  ```
- `.env.claude`：
  ```dotenv
  CLAUDE_SETTINGS_JSON=claude-settings.json
  ```

真实文件可由模板复制：

```bash
cp codex-auth-template.json codex-auth.json
cp codex-config-template.toml codex-config.toml
cp claude-settings-template.json claude-settings.json
```

`codex-auth.json`、`codex-config.toml`、`claude-settings.json` 已加入 `.gitignore`。如果 `.env.<agent>` 缺少对应路径，或路径不存在，脚本会直接报错退出。

如果只是本机快速验证，也可以直接修改 `.env.codex` / `.env.claude` 指向用户目录下已有配置，例如 `/Users/<you>/.codex/auth.json`、`/Users/<you>/.codex/config.toml` 或 `/Users/<you>/.claude/settings.json`。这种方式适合临时 smoke test；提交前应确认 `.env.<agent>` 是否仍应保持仓库默认相对路径。

env-file 规则：

- 如果命令行传了 `--env-file <path>`，使用该文件。
- 如果没有显式传 `--env-file`，inference 脚本会自动使用该 agent 对应文件，例如 `.env.codex` 或 `.env.claude`。
- 如果对应 `.env.<agent>` 不存在，脚本会在启动 inference 前报错退出，避免误用空环境运行。
- runner 不把 `.env.<agent>` 传给 `docker run --env-file`；它只读取里面的文件路径，并把对应文件只读挂载到容器固定路径。

不同 agent 的推荐 env-file：

- `--agent codex`：默认使用 `.env.codex`，缺失时报错。
- `--agent claude`：默认使用 `.env.claude`，缺失时报错。
- 自定义 `--agent-command`：按该命令需要显式传对应 env 文件。

挂载路径和模型解析：

- Codex：`CODEX_AUTH_JSON` 挂载到 `/home/node/.codex/auth.json`，`CODEX_CONFIG_TOML` 挂载到 `/home/node/.codex/config.toml`；模型名从 `CODEX_CONFIG_TOML` 顶层 `model = "..."` 解析。
- Claude Code：`CLAUDE_SETTINGS_JSON` 挂载到 `/home/node/.claude/settings.json`；模型名从 settings JSON 的 `env.ANTHROPIC_MODEL` 解析。

模型名会作为输出目录标签、评测报告标签和默认 `run-id` 的 model 段。

Claude 默认使用仓库根目录的 `.env.claude`，通常不需要显式传 `--env-file`：

```bash
bash scripts/run_univer_agent_eval.sh --agent claude --task-id 54513
```

Codex 默认使用仓库根目录的 `.env.codex`，通常不需要显式传 `--env-file`：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --task-id 54513
```

Codex 容器内固定使用 `--dangerously-bypass-approvals-and-sandbox`，因为外层已经由 Docker task workspace 隔离；不要在 `.env.codex` 中配置额外 Codex CLI 参数。

## 快速开始

默认数据集是 `spreadsheetbench_verified_400`。未显式传 `--run-id` 时，脚本会自动生成：

```text
<agent>-<model>-<dataset>-<scope>-YYYYMMDD-HHMMSS
```

例如：

```text
codex-gpt-5-3-codex-spark-verified400-first50-20260521-143000
```

用 Codex 跑一道题并自动评测：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --task-id 54513
```

用 Claude 跑一道题并自动评测：

```bash
bash scripts/run_univer_agent_eval.sh --agent claude --task-id 54513
```

用 Codex 跑默认数据集前 80 题并自动评测：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --limit 80
```

用 Claude 跑默认数据集前 80 题并自动评测：

```bash
bash scripts/run_univer_agent_eval.sh --agent claude --limit 80
```

前 80 题并发跑 10 个 task：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --limit 80 --workers 10
bash scripts/run_univer_agent_eval.sh --agent claude --limit 80 --workers 10
```

使用自定义容器内命令：

```bash
bash scripts/run_univer_agent_eval.sh \
  --agent-command 'my-agent --prompt-file "$SPREADSHEETBENCH_PROMPT_FILE"' \
  --env-file .env.my-agent \
  --task-id 54513
```

## 常用参数

指定数据集：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --dataset sample_data_200 --task-id 54513
```

只跑前 N 道题：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --limit 10
```

只跑指定题目：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --task-id 54513 --task-id 59196
```

控制 task 级并发数，默认是 5：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --limit 10 --workers 3
```

指定 Docker 命令：

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --docker-bin docker --task-id 54513
```

最终输出会写到：

```text
data/<dataset>/outputs/univer_agent_<model>/
```

## Task Workspace

host runner 为每个 task 创建独立目录，并用 solver Docker image 预导入每个 case 的 `input.univer`：

```text
.runs/univer-agent/<run-id>/<task-id>/task/
  prompt.md
  cases/
    case_1/input.xlsx
    case_1/input.univer
    case_2/input.xlsx
    case_2/input.univer
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
  -v /abs/path/codex-auth.json:/home/node/.codex/auth.json:ro \
  -v /abs/path/codex-config.toml:/home/node/.codex/config.toml:ro \
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

容器不能访问 answer 文件、dataset 根目录、其他 task workspace 或 report。agent 应使用当前 task 内预导入的 `input.univer`，并通过 `univer inspect/search/pipe/run/help/export` 完成修改和导出。

## 日志和结果

最先看 run summary：

```text
.runs/univer-agent/<run-id>/summary.json
```

每个 task 的 Docker 日志在：

```text
.runs/univer-agent/<run-id>/<task-id>/task/logs/docker.command.txt
.runs/univer-agent/<run-id>/<task-id>/task/logs/<agent>.events.jsonl
.runs/univer-agent/<run-id>/<task-id>/task/logs/codex.final.md
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
jq '{metadata, counts: (.tasks | group_by(.status) | map({status: .[0].status, count: length})), tasks: [.tasks[] | {id, status, duration_seconds, error}]}' \
  .runs/univer-agent/<run-id>/summary.json
```

如果 Docker 阶段失败：

```bash
cat .runs/univer-agent/<run-id>/<task-id>/task/logs/docker.timing.json
cat .runs/univer-agent/<run-id>/<task-id>/task/logs/docker.command.txt
```

如果 Docker 成功但任务失败，通常是缺少某个输出：

```bash
find .runs/univer-agent/<run-id>/<task-id>/task/outputs -maxdepth 3 -type f
```

如果 evaluation 不通过，看报告和标准输出文件：

```bash
jq '.accuracy, .evaluate.results' report/<run-id>.json
ls data/<dataset>/outputs/<setting>_<model>/<case>_<task-id>_output.xlsx
```

answer 文件只用于人工离线排查，不会挂载进 Docker 容器。
