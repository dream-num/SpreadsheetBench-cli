# Agent 指令

- 当用户只说开始/运行测试且没有进一步说明时，按 `RUN.md` 的 SpreadsheetBench 流程执行。
- 启动命令：
  `bash scripts/run_univer_agent_eval.sh --agent <agent> --task-id <task-id> --run-id <run-id>`
- `run-id` 根据 agent、数据集、任务范围命名，并追加日期时间，如果是临时任务，添加tmp-前缀。
- 常用参数：`--agent`、`--agent-command`、`--dataset`、`--task-id`、`--limit`、`--run-id`、`--agent-timeout`。详情见 `RUN.md`。
- 沙箱中运行 `codex`、`claude` 等外部 agent 时，如遇网络、认证、DNS、模型请求或依赖下载问题，按疑似沙箱限制处理，使用提权方式重跑测试命令。

## 数据集

- `sample_data_200`：样例数据集，200 道题。用户简写为 `sample`、`sample200`、`200` 或 `s200` 时，自动推断为该数据集。
- `all_data_912_v0.1`：完整数据集，912 道题。用户简写为 `all`、`full`、`912`、`all912` 或 `full912` 时，自动推断为该数据集。
- `spreadsheetbench_verified_400`：SpreadsheetBench Verified 数据集，400 道题；默认数据集。用户简写为 `verified`、`verify`、`v400`、`verified400` 或 `400` 时，自动推断为该数据集。

## 运行后分析

- 先看 `.runs/univer-agent/<run-id>/summary.json`：确认任务数、`ok/error/timeout`、耗时最高的任务。
- 再看 `report/<run-id>.json` 和 `outputs/eval_*<run-id>.json`：统计准确率、失败 case、超时 case。
- 对失败或超时 case，按以下顺序定位原因：
  1. 读该 case 的 `task/prompt.md`，确认 `answer_position` 和任务要求。
  2. 查 `task/logs/docker.output.txt`、`docker.stderr.txt`、`docker.timing.json`。
  3. 对比 output 与 golden 在 `answer_position` 内的差异；必要时同时检查值、公式、数字格式、样式、空白行和工作表结构。
  4. 判断失败类型：理解错误、范围/边界错误、值类型或格式错误、工具链错误、超时/网络问题。
- 逐题详细分析时，每次只分析一道题，并明确区分问题归因：agent 自身题意理解/推理/验证问题，`univer-cli` 命令或 API 问题，skill 指引问题，prompt/runner/评测流程问题，或数据/题目歧义等其它问题。
- 逐题分析必须写出 agent 操作时的卡点：是否有命令误用、失败重试、API 探测、硬编码范围、排序/截断前后顺序风险、验证不足、耗时异常、或接近违反 `answer_position`/文件访问约束的行为。
- 不要只依赖评测 JSON。评测程序较简单时，也要检查最终 `output.xlsx`：优先用 `openpyxl` 直接读取 output 和 golden 的 `.xlsx`，检查 `answer_position` 内的值、公式、数字格式、样式、空白区、工作表结构、排序、截断、导出结果或范围外污染；只有需要 Univer 可见状态或 CLI 行为对照时，再把 `.xlsx` 临时导入为 `.univer` 辅助检查。
- 对正确 case 也要扫日志中的可恢复问题，尤其是 `cp: omitting directory`、`Unknown argument`、`Missing workbook package file`、`Range is out of bounds`、`Sheet not found`、`python/jq not found`、`npm install`、`univer export` 崩溃等。报告中区分“最终正确但过程有问题”和“评测失败”。
- 用户要求详细分析时，输出两部分：失败/超时原因报告；正确 case 执行问题与优化建议。

## 已知错题与 issue 状态

逐题错因分析时先查本节。已知问题不要重复归因给 agent；如果新 run 中同一 task 出现不同失败形态，需要明确说明“不同于已知问题”的新证据。

### 已知题目

| 数据集 | task-id | 当前状态 | issue 状态 | 分析处理 |
| --- | --- | --- | --- | --- |
| `spreadsheetbench_verified_400` | `283-32` | 题目 `answer_position` 使用整列范围 `A:G`，当前评测程序无法解析；agent 输出值与 golden 一致。 | 本地记录：`issue/283-32-answer-position-column-range-eval-gap.md`；不是 `univer-cli` 上游问题，未报上游 issue。 | 逐题错因分析时跳过，不归因给 agent 或 `univer-cli`。 |
| `spreadsheetbench_verified_400` | `262-17` | 已知 `univer-cli` / 导出相关问题。早期 drawing export crash 在新版已修；后续仍有 data validation `type=""` 导出兼容问题。 | 本地记录：`issue/262-17-export-drawing-crash-date-fallback.md`、`issue/262-17-export-invalid-data-validation-empty-type.md`；已给 `univer-cli` 仓库报过 bug。 | 作为已知工具链问题处理；除非出现新失败形态，否则不要重复归因给 agent。 |
| `spreadsheetbench_verified_400` | `42930` | 数据文件名不匹配：golden 文件为 `1_43930_golden.xlsx`，task id 为 `42930`，导致评测发现不到有效 case。 | 暂无上游 issue；属于数据/题目文件问题。 | 汇总统计时单独列出，不归因给 agent 或 `univer-cli`。 |

### 已报上游通用问题

| GitHub issue | 问题 | 关联 SpreadsheetBench 题目 | 本地记录 |
| --- | --- | --- | --- |
| https://github.com/dream-num/univer-cli/issues/296 | `FILTER` 动态数组公式导出后，Excel 修复并删除公式，spill 缓存值丢失。 | `220-7665`, `323-54085`, `340-56378`, `387-58499`；相关现象：`328-54667`, `399-59884`。`130-33722` 已在 2026-05-25 当前镜像单题重跑通过，不再按该 issue 归类。 | `issue/296-filter-dynamic-array-export-excel-repair.md` |
| https://github.com/dream-num/univer-cli/issues/297 | `import/export` roundtrip 后 `styles.xml` 出现空 `<fill/>`，导致 `openpyxl` 无法读取导出 xlsx。 | `193-51090`, `215-3911`, `258-35742`, `315-52541`, `332-55060`, `384-57989` 等。 | `issue/297-empty-fill-openpyxl-roundtrip.md`；复现包在 `debug/univer-empty-fill-openpyxl-repro.zip`。 |

### 最新 Codex 未调查 / 未记录错题

- run-id: `codex-gpt-5-5-verified400-all-20260523-230050`
- 口径：该 run 的失败 / 缺评测项中，未记录到上方“已知题目”表的都算；不按是否已有 `analaysix/` 逐题报告排除。
- 错题列表（65 题）：
  - `003-22-47`, `007-41-47`, `029-469-9`, `038-80-42`, `046-118-50`, `047-130-9`, `048-142-19`, `049-146-49`, `061-203-15`, `092-387-16`, `095-398-14`, `100-414-20`
  - `108-486-17`, `112-496-34`, `115-524-31`, `117-534-26`, `118-535-20`, `132-37900`, `169-48643`, `176-48983`, `177-49036`, `180-49300`, `185-50193`
  - `192-50952`, `193-51090`, `200-52575`, `207-54590`, `211-1925`, `213-3002`, `215-3911`, `217-5835`, `220-7665`, `233-13284`, `234-14240`, `245-32023`
  - `246-32093`, `258-35742`, `266-37462`, `280-42216`, `284-43436`, `288-44628`, `291-45738`, `292-45944`, `300-50486`, `309-51680`, `313-52305`, `315-52541`
  - `318-53161`, `323-54085`, `328-54667`, `329-54717`, `332-55060`, `334-55427`, `336-55965`, `340-56378`, `359-43213`, `361-44017`, `372-55977`, `375-56786`
  - `376-56915`, `377-56953`, `384-57989`, `387-58499`, `399-59884`

## 修复与实验原则

- 优先从高价值、明显错误、可通用复现的问题开始修复，例如 CLI 参数误用、导入/导出失败、运行时超时、值类型/格式处理、样式保留、范围边界、工作表识别等。
- 修复必须针对 `univer-cli`、runner、评测流程或当前程序的通用问题；不得通过读取答案、硬编码 task id、硬编码具体题目内容、改 golden、改 evaluation 口径等方式提升分数。
- 不得变更题目提示中的任务信息、`answer_position`、输入数据或评测数据。新增或修改提示词时，只能加入通用规则、通用工具使用规范或通用坑点提醒，不能对特定题目、特定 case、特定字段值做特化描述。
- 如果只是修改 agent prompt 文案或通用提示规则，不要求新增/修改 UT，也不强制按 TDD 流程执行；除非用户明确要求，不要为了这类改动新增或修改 UT 断言。验证以生成后的 prompt 检查、相关 case 重跑、日志分析和 `fix-logs/` 记录为主。
- `issue/` 用来记录尚未修复或刚发现的通用问题、根因分析和候选改进方向，尤其是 `univer-cli`、skill、Univer API/导入导出、agent 执行策略等问题；不要把已实施修复的实验结果只写在 `issue/`。
- `fix-logs/` 用来记录已经实施并验证过的修复或实验结果，包括基线 run-id、实验 run-id、改动内容、准确率/失败变化、剩余风险和后续建议。
- 一次只实验一个改进点。每次改动前说明假设和预期影响；改动后用同一数据集、同一 agent/env、同一任务范围重跑，避免混入其他变量。
- 只有在重跑结果相对基线有可验证提升时，才保留该改动；否则回滚该实验改动并继续分析下一个候选点。
- 如果改进有效，在 `fix-logs/` 下新增一篇 Markdown 记录：基线 run-id、实验 run-id、改动内容、影响范围、准确率/失败数变化、仍未解决的问题和风险。
- 有效改进记录完成后再提交 commit。commit 应只包含该单一改进及对应 `fix-logs` 记录，不夹带无关重构或其他实验。
- 用户要求隔离开发时，在项目 `.worktree/` 目录下新建 git worktree 和新分支执行实验；不要污染当前工作区，也不要回滚用户已有未提交改动。

## 创建 GitHub univer-cli issue

- 向 `dream-num/univer-cli` 或本地 `/Users/otime/project/univer-cli` 对应上游仓库创建 GitHub issue 前，必须先把拟创建的目标仓库、标题、正文、标签和附件/复现文件说明发给用户确认。
- 未经用户明确确认，不要执行 `gh issue create`，也不要用其它工具或 API 创建上游 issue。
- issue 标题和正文主体默认使用中文；除非用户明确要求英文，不要改用英文撰写上游 issue。
- issue 正文应独立且聚焦 issue 本身，优先写：问题描述、实际表现、期望表现、最小复现步骤、已验证的根因线索和影响范围；不要把 SpreadsheetBench 运行分析写成正文主线。
- 如果复现依赖相关文件，应直接作为 GitHub issue 附件或公开可访问复现包提供；不要只写本机路径，也不要假设上游维护者能访问本地文件。需要附件时，先询问用户是否整理并上传。
- 如果当前工具链无法上传附件（例如 `gh issue create/comment/edit` 不支持直接上传本地 zip），必须在创建或更新 issue 前明确告诉用户附件无法由当前工具上传。issue 正文中只能写“参考附件 `xxx.zip`”这类附件文件名，不要写本地路径；同时在对话中把已经准备好的本地附件路径交给用户，让用户手动上传，或由用户确认公开链接/Gist 等替代方案。
- SpreadsheetBench 相关内容放在后面的“关联背景”小节，只简要说明发现来源、run-id、task-id、评测影响和本地详细记录路径。
- 创建完成后，记录 issue URL；除非用户要求，不要自动修改本地 issue 文档或提交新 commit。

# 语言
- 对话始终使用中文
