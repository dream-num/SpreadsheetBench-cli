# Agent 指令

- 当用户只说开始/运行测试且没有进一步说明时，按 `RUN.md` 的 SpreadsheetBench 流程执行。
- 启动命令：
  `bash scripts/run_univer_agent_eval.sh --agent <agent> --task-id <task-id> --run-id <run-id>`
- `run-id` 根据 agent、数据集、任务范围命名，并追加日期时间，如果是临时任务，添加tmp-前缀。
- 常用参数：`--agent`、`--agent-command`、`--dataset`、`--task-id`、`--limit`、`--workers`、`--run-id`、`--agent-timeout`、`--env-file`。详情见 `RUN.md`。
- 沙箱中运行 `codex`、`claude` 等外部 agent 时，如遇网络、认证、DNS、模型请求或依赖下载问题，按疑似沙箱限制处理，使用提权方式重跑测试命令。

## 数据集

- `sample_data_200`：样例数据集，200 道题。用户简写为 `sample`、`sample200`、`200` 或 `s200` 时，自动推断为该数据集。
- `all_data_912_v0.1`：完整数据集，912 道题。用户简写为 `all`、`full`、`912`、`all912` 或 `full912` 时，自动推断为该数据集。
- `spreadsheetbench_verified_400`：SpreadsheetBench Verified 数据集，400 道题；默认数据集。用户简写为 `verified`、`verify`、`v400`、`verified400` 或 `400` 时，自动推断为该数据集。

## 运行与分析排除题目

- 有些题目属于已确认无有效复测信号的已知问题，不再运行、不再逐题分析；即使用户要求跑全量、跑错题表上所有错题、分析错题表全部错题，也要从任务范围和未调查候选中排除，并在汇报中说明这些题目按本节规则跳过。这不是普通已知错题清单，只记录因评测或工具链已确认不值得重复消耗运行资源的题目。
- 当前排除清单：
  - `130-9`、`283-32`、`49300`：评测程序 bug。

## 运行后分析

- 先看 `.runs/univer-agent/<run-id>/summary.json`：确认任务数、`ok/error/timeout`、耗时最高的任务。
- 再看 `report/<run-id>.json` 和 `outputs/eval_*<run-id>.json`：统计准确率、失败 case、超时 case。
- 需要快速抽取报告关键信息时，使用 `scripts/extract_report_summary.py` 从 `report/<run-id>.json` 生成精简 JSON，例如：
  `python3 scripts/extract_report_summary.py report/<run-id>.json --output tmp/<run-id>.summary.json`
  输出包含运行元信息、case/task 汇总、整体平均耗时、ok 任务平均耗时、`PASS/FAIL/TIMEOUT/ERROR/NOT_RUN` 计数、失败/超时/未执行 task 列表、最慢任务、按 `instruction_type` 分组统计和逐 task 压缩状态。临时提取结果、一次性中间 JSON/TSV 和人工分析草稿默认放在仓库根目录 `tmp/` 下；除非用户明确要求，不要把 `tmp/` 里的临时产物作为正式记录或提交内容。
- 根目录 `wrong-report-matrix.univer` 用来累计记录不同报告中的错题稳定性；以后只更新这个 `.univer` 文件，不保留配套 `.xlsx`。每个 sheet 按 `<agent>-<model>-<题集>` 命名，例如 `codex-gpt-5.5-verified400`；第 1 行是表头，第 2 行固定为错题数统计行：`A2` 写 `错题数`，各报告列在同一个单元格中分别统计失败和未执行，公式格式为 `="F:"&COUNTIF(<报告列>3:<报告列>1000,"FAIL")&"，NR:"&COUNTIF(<报告列>3:<报告列>1000,"NOT_RUN")`，显示如 `F:52，NR:11`；不要只写 `FAIL+NOT_RUN` 合计数。task 数据从第 3 行开始。行只保留至少在该 sheet 任一报告中失败过一次的 task；基础列固定为 `task_id`、`备注`，后面每个报告一列。报告列名使用简短 run-id：在不丢失辨识度的前提下去掉已由 sheet 名表达的 agent/model/题集公共前缀，例如 `codex-gpt-5-5-verified400-all-20260525-153934` 在 `codex-gpt-5.5-verified400` sheet 中记为 `20260525-153934`。报告列按时间从左到右追加。每个报告列必须显式写状态：通过写 `PASS`，评测失败或超时写 `FAIL`，报告中缺少该 task、缺评测项或空 `test_case_results` 写 `NOT_RUN`；不要用空白表示通过，避免通过和未执行混淆。新增全量报告后，应根据 `outputs/eval_*<run-id>.json` 在对应 agent/model/题集 sheet 末尾追加一列，并在第 2 行补充该报告列的分项 `COUNTIF` 公式；如果出现新的错题，需要在该 sheet 第 3 行及之后追加新行。新增报告列或新增错题行后还应把条件格式扩展到当前报告区域（从 `C3` 到最新报告列、最新 task 行）：`PASS` 绿色、`FAIL` 红色、`NOT_RUN` 黄色；不要预先扩展 sheet 尺寸。不要添加题目序号列、`classification` 列或 summary sheet；稳定过、稳定错、偶发错通过横向查看 `PASS`/`FAIL`/`NOT_RUN` 判断。
- 用户说“错题表上所有错题”或“错题表所有错题”时，指对应 sheet 第 3 行以后所有有 `task_id` 的历史失败/未执行 task，也就是任一报告列曾经出现过 `FAIL` 或 `NOT_RUN` 的行。这不是最新报告仍失败/未执行的数量。用户说“错题表最新错题”或“当前最新错题”时，指对应 sheet 最右侧最新报告列为 `FAIL` 或 `NOT_RUN` 的 task，数量以该列第 2 行公式中的 `F` 与 `NR` 分项为准。用户说“错题表未调查题目”或“未调查候选”时，指“错题表上所有错题”中 `备注` 列为空的 task，不要求最新报告列仍为 `FAIL` 或 `NOT_RUN`；已有备注的问题不要重复算未调查，如果新 run 出现不同失败形态，需要明确说明和备注列已知问题的差异。
- 对失败或超时 case，按以下顺序定位原因：
  1. 读该 case 的 `task/prompt.md`，确认 `answer_position` 和任务要求。
  2. 查 `task/logs/docker.output.txt`、`docker.stderr.txt`、`docker.timing.json`。
  3. 对比 output 与 golden 在 `answer_position` 内的差异；必要时同时检查值、公式、数字格式、样式、空白行和工作表结构。
  4. 判断失败类型：理解错误、范围/边界错误、值类型或格式错误、工具链错误、超时/网络问题。
- 当前 `evaluation/evaluation.py` 的正式判分逻辑使用 `openpyxl.load_workbook(..., data_only=True)` 读取 output 和 golden，然后只比较 `answer_position` 内的 `cell.value`；公式文本、样式、填充色和字体色默认不参与判分（颜色比较代码是注释状态）。分析错题时必须先按这个逻辑复现评测结果；如果 output 与 golden 的 `data_only=True` 值一致但评测仍 FAIL，应优先检查 `answer_position` 解析、sheet 名、不可见字符（例如 NBSP `\u00A0`）、范围格式、文件路径和 openpyxl 读取异常，不要仅因公式或样式差异就归因为 agent 输出错误。
- 逐题详细分析时，每次只分析一道题，并明确区分问题归因：agent 自身题意理解/推理/验证问题，`univer-cli` 命令或 API 问题，skill 指引问题，prompt/runner/评测流程问题，或数据/题目歧义等其它问题。
- 逐题分析必须写出 agent 操作时的卡点：是否有命令误用、失败重试、API 探测、硬编码范围、排序/截断前后顺序风险、验证不足、耗时异常、或接近违反 `answer_position`/文件访问约束的行为。
- 不要只依赖评测 JSON。评测程序较简单时，也要检查最终 `output.xlsx`：优先用 `openpyxl` 直接读取 output 和 golden 的 `.xlsx`，检查 `answer_position` 内的值、公式、数字格式、样式、空白区、工作表结构、排序、截断、导出结果或范围外污染；只有需要 Univer 可见状态或 CLI 行为对照时，再把 `.xlsx` 临时导入为 `.univer` 辅助检查。
- 对正确 case 也要扫日志中的可恢复问题，尤其是 `cp: omitting directory`、`Unknown argument`、`Missing workbook package file`、`Range is out of bounds`、`Sheet not found`、`python/jq not found`、`npm install`、`univer export` 崩溃等。报告中区分“最终正确但过程有问题”和“评测失败”。
- 用户要求调查、分析或复核问题时，默认只读检查并向用户输出详细调查结论，不要自动写入 `wrong-report-matrix.univer` 或其它 `.univer` 文件。
- 用户要求详细分析时，输出两部分：失败/超时原因报告；正确 case 执行问题与优化建议。

## 已知错题与 issue 状态

逐题错因分析时先查根目录 `wrong-report-matrix.univer` 中对应 agent/model/题集 sheet 的 `备注` 列。已知问题、上游 issue、数据问题、历史失败形态和已修复但矩阵尚未重跑的状态都记录在该列；不要在 `AGENTS.md` 维护静态已知错题清单。

只有用户明确要求“记录到矩阵”、“更新备注”、“写入 `wrong-report-matrix.univer`”或同等含义时，才允许把调查结论写入 `wrong-report-matrix.univer`。写入前应说明要写入的 sheet、单元格/范围和原因；未得到明确要求时，即使已经确认新根因，也只在对话中报告结论。

需要找当前最新错题、稳定错题、偶发错题或未调查候选时，优先用 `univer inspect workbook wrong-report-matrix.univer` 确认 sheet 和 used range，再用 `univer pipe out wrong-report-matrix.univer --range '<sheet>!A1:ZZ1000' --format tsv` 或 `univer inspect range` 读取可见表格。

判断“未调查 / 未记录”时，以 `.univer` 中对应 sheet 的历史失败 task 行为准：第 3 行以后有 `task_id`，且 `备注` 列为空的 task，才作为新的逐题分析候选；不要求最新报告列仍为 `FAIL`。已有备注的问题不要重复归因给 agent；如果新 run 中同一 task 出现不同失败形态，需要明确说明“不同于备注列已知问题”的新证据。

## 最近连续 4 次稳定通过错题

以下题目来自 `wrong-report-matrix.univer` 的 `codex-gpt-5.5-verified400` sheet，最近连续多次均为 `PASS`。用户要求跑全量错题、错题表上所有错题或错题表所有错题时，默认可跳过这些题目，并在汇报中说明这些题目因最近稳定通过而跳过；如果用户明确要求复测稳定通过题目，再重新纳入任务范围。

- 最近 4 列：`20260527-220546`、`allwrong96-exskip-w5-timeout480-20260527-232251`、`allwrong96-workflowplan-w15-timeout480-20260528-152629`、`allwrong96-planrevert-w15-timeout480-20260528-165520`。
- 当前稳定通过题目：`23-24`、`262-17`、`398-14`、`414-20`、`535-20`、`3911`、`7665`、`14240`、`33722`、`35742`、`38074`、`43213`、`44628`、`46897`、`50952`、`51090`、`52541`、`52575`、`54085`、`54717`、`55060`、`55965`、`56378`、`56419`、`57989`、`58499`、`157-4`、`208-20`、`409-45`、`448-11`、`38537`、`54638`、`15387`。

## 修复与实验原则

- 优先从高价值、明显错误、可通用复现的问题开始修复，例如 CLI 参数误用、导入/导出失败、运行时超时、值类型/格式处理、样式保留、范围边界、工作表识别等。
- 修复必须针对 `univer-cli`、runner、评测流程或当前程序的通用问题；不得通过读取答案、硬编码 task id、硬编码具体题目内容、改 golden、改 evaluation 口径等方式提升分数。
- 不得变更题目提示中的任务信息、`answer_position`、输入数据或评测数据。新增或修改提示词时，只能加入通用规则、通用工具使用规范或通用坑点提醒，不能对特定题目、特定 case、特定字段值做特化描述。
- 如果只是修改 agent prompt 文案或通用提示规则，不要求新增/修改 UT，也不强制按 TDD 流程执行；除非用户明确要求，不要为了这类改动新增或修改 UT 断言。验证以生成后的 prompt 检查、相关 case 重跑、日志分析和 `fix-logs/` 记录为主。
- `issue/` 用来记录尚未修复或刚发现的通用问题、根因分析和候选改进方向，尤其是 `univer-cli`、skill、Univer API/导入导出、agent 执行策略等问题；不要把已实施修复的实验结果只写在 `issue/`。
- `fix-logs/` 用来记录已经实施并验证过的修复或实验结果，包括基线 run-id、实验 run-id、改动内容、准确率/失败变化、剩余风险和后续建议。
- 一次只实验一个改进点。每次改动前说明假设和预期影响；改动后用同一数据集、同一 agent/env、同一任务范围重跑，避免混入其他变量。
- 判断实验是否有效时，不能只看最终准确率、失败数或 PASS/FAIL 变化。先用评测 JSON 找出相对基线的新增 PASS、新增 FAIL、仍 FAIL 和超时/运行异常；再按“运行后分析”的逐题流程读变化题日志、prompt、output/golden 和 `answer_position` 内差异，判断 agent 行为是否真的因本次改动改善或退化。报告中必须区分：本次改动导致的真实退化；本次改动带来的真实改进；评测/数据/标注冲突；工具链或导出问题；随机执行波动；以及最终正确但过程仍有问题。
- 对 prompt、skill 指引或 agent 执行策略类实验，尤其要检查日志中是否实际出现并遵守了新增要求，例如固定 heading、plan、plan review、反证样本、值类型验证、边界检查等。新增要求被执行但最终仍 FAIL 时，不能立即判定为 prompt 退化；必须分析 FAIL 是否来自新增要求本身的错误引导、agent 后续违背/改写了自己的 plan、验证样本选择不独立、题目/answer_position 标注冲突，或其它已知工具链/数据问题。
- 只有在日志和 workbook 证据显示改动带来可复用的真实收益，且没有引入更高风险的通用错误模式时，才保留该改动并继续扩大范围验证。若总分下降但逐题日志显示新增要求修复了目标行为、失败主要来自已知标注/评测问题或随机执行，先记录结论并考虑缩小或调整实验，不要直接回滚。若日志证据显示改动引入了新的通用错误模式，或没有产生可复用收益，再回滚该实验改动并继续分析下一个候选点。
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
