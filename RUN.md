# 运行 Univer Agent 评测

当前主流程是 Docker-only 黑盒执行：

```text
host runner -> /task workspace -> Docker solver -> outputs/case_N/output.xlsx -> evaluation/report
```

host runner 只负责准备 `/task`、把每个 case 的输入 artifact 导入成 target univerfile、收集输出和执行评测；解题、修改 workbook、导出 `output.xlsx` 都在 Docker solver 内完成。runner 会先把 `input.xlsx` 临时复制到 case 目录，再在 solver image 内执行 `univer import --file /task/cases/case_N/input.xlsx /task/cases/case_N/workbook.univer --json`，由 CLI 创建 target workbook 和隐藏 sidecar `/task/cases/case_N/.workbook.univer.sac`。raw input 拷贝是 runner 中间产物，准备完成后会移除，不作为容器内解题 source 保留。

benchmark 约束由 task-local `/task/AGENTS.md` 承载；prompt 只保留动态任务 envelope。这样 Codex 会优先遵循 workspace 内的硬约束，也避免把 SpreadsheetBench 专属约束放进通用 skill。

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

使用本地最新版 `univer-cli` 构建 SaC 实验镜像时，使用独立镜像名：

```bash
bash scripts/build_agent_docker_from_local_univer_cli.sh \
  --repo /Users/morris/Developer/univer/univer-cli \
  --tag spreadsheetbench-univer-cli-agent-local
```

镜像内包含 Node/npm、bash、`univer-cli@latest`、Codex、Claude 和 Univer 相关 skills。SpreadsheetBench 专属约束不依赖 benchmark skill，而是由 runner 写入 `/task/AGENTS.md`。

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

指定解题镜像：

```bash
bash scripts/run_univer_agent_eval.sh \
  --agent codex \
  --docker-image spreadsheetbench-univer-cli-agent-sac \
  --run-id sac-codex-gpt-5-5-verified400-task54513-$(date +%Y%m%d-%H%M%S) \
  --task-id 54513
```

SaC 实验 run-id 统一使用 `sac-` 前缀；如果不显式传 `--run-id`，默认
run-id 仍按普通评测规则生成。

最终输出会写到：

```text
data/<dataset>/outputs/univer_agent_<model>/
```

## Task Workspace

host runner 为每个 task 创建独立目录。agent 在容器内从 `/task` 启动，
`/task/AGENTS.md` 是唯一的 benchmark 指令文件：

```text
.runs/univer-agent/<run-id>/<task-id>/task/
  AGENTS.md
  prompt.md
  cases/
    case_1/workbook.univer
    case_1/.workbook.univer.sac/
      AGENTS.md
      inspect-scripts/
      migrations/
      types/
    case_2/workbook.univer
    case_2/.workbook.univer.sac/
      AGENTS.md
      inspect-scripts/
      migrations/
      types/
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
instruction_type
answer_position
output_path
```

host runner 不会生成 `spreadsheet_content` 或 `workbook_context.md`，也不会挂载 answer 文件。

容器不能访问 answer 文件、dataset 根目录、其他 task workspace 或 report。agent 应使用当前 task 内准备好的 `workbook.univer` 和隐藏 sidecar `.workbook.univer.sac`，不要读取或重新导入 raw input。所有 benchmark 硬约束和 SaC 使用方式写在 `/task/AGENTS.md`。

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
jq '{metadata, counts: (.tasks | group_by(.status) | map({status: .[0].status, count: length})), tasks: [.tasks[] | {id, status, duration_seconds, error}]}' \
  .runs/univer-agent/<run-id>/summary.json
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

```bash
jq '.accuracy, .evaluate.results' report/<run-id>.json
ls data/<dataset>/outputs/<setting>_<model>/<case>_<task-id>_output.xlsx
```

answer 文件只用于人工离线排查，不会挂载进 Docker 容器。
