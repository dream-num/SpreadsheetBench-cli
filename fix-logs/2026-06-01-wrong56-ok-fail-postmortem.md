# wrong56 runner-ok / evaluator-fail 复盘

## 范围

Run: `sac-local-cli-skill-success-criteria-wrong56-20260601-193000`

证据文件：

- Runner summary: `.runs/univer-agent/sac-local-cli-skill-success-criteria-wrong56-20260601-193000/summary.json`
- Eval report: `outputs/eval_univer_agent_gpt-5.5_sac-local-cli-skill-success-criteria-wrong56-20260601-193000.json`
- Combined report: `report/sac-local-cli-skill-success-criteria-wrong56-20260601-193000.json`

分桶结果：

- `ok/PASS`: 15
- `ok/FAIL`: 36
- `error/FAIL`: 5

这份记录聚焦 `ok/FAIL`：agent 已完成运行、产出了 `output.xlsx`，但仍然没有通过正式 evaluator。

## 方法

对抽样 case 逐个做以下检查：

1. 读取 `summary.json` 和 eval JSON，确认 `runner status == ok` 且 evaluator 结果为 `FAIL`。
2. 使用 `openpyxl.load_workbook(..., data_only=True)` 复现 evaluator-facing 对比。
3. 只在 `answer_position` 内对比 output 和 golden。
4. 只在离线复盘中使用支持引号和 NBSP trim 的 parser，用来区分 evaluator 解析 bug 和真实 workbook 输出差异。

Runtime prompt 变更不能让 agent 访问 golden。Golden 只作为离线 postmortem 证据使用。

## 发现

### 1. 部分失败是 evaluator 或标注解析 bug，不是 agent workbook 失败

`49300`

- Prompt `answer_position`: `\u00a0'Sheet1'!C2:C3`
- 按正式 evaluator 风格解析会失败，因为 sheet name 保留了开头 NBSP，变成了 `"\u00a0'Sheet1"`。
- 使用 quote/NBSP-aware 的离线对比时，`Sheet1!C2:C3` 零差异通过。
- 分类：evaluator / annotation bug。
- 合同影响：不修改 benchmark 数据或 evaluator parser 的情况下，prompt/AGENTS 无法在 runtime 解决这个问题。它应该和 prompt 质量问题分开追踪。

`130-9`

- Prompt `answer_position`: `'b2b, sez, de'!A5:V10`
- 正式 evaluator 直接按逗号 split，导致带引号的 sheet name 被错误拆开。
- quote-aware 对比仍然能看到真实输出差异：
  - `b2b, sez, de!E7`: golden `5780.83`，output `"C"`
  - `b2b, sez, de!E8`: golden `24059.15`，output `"C"`
  - `b2b, sez, de!E9`: golden `12212.82`，output `"C"`
- 分类：混合问题。存在 evaluator parser bug，但这次 rerun 也确实有 column mapping 输出错误。
- 合同影响：evaluator parsing 应该单独修；prompt/skill 仍需要加强 header mapping assertions，避免某个目标列错位或误映射后仍然通过 SaC verify。

`45944`

- Prompt `answer_position`: `G4:G6, G11:G13, G20:G22`
- 正式 evaluator 风格解析会在 `G11:G13` 和 `G20:G22` 前面的空格处失败。
- quote/trim-aware 对比仍然能看到真实 row-anchor 差异：
  - `G12`: golden `False`，output `True`
  - `G13`: golden `True`，output `False`
  - `G21`: golden `False`，output `True`
  - `G22`: golden `True`，output `False`
- 分类：混合问题。既有 evaluator range splitting/trim bug，也有真实 row-anchor mismatch。
- 合同影响：保留已有 row-anchor 指导；同时对不连续 `answer_position` window 增加强 assertion 要求。

### 2. Agent 对精确文本的保留仍然偏弱

`50486`

- 差异：
  - `A4`: golden `LOSCAM`，output `Loscam`
  - `A5`: golden `LOSCAM`，output `Loscam`
- 生成的 plan 明确选择了 `CHEP`, `CHEP`, `Loscam`, `Loscam`，在 workbook header 和已有值都显示全大写 label 的情况下，仍然使用了 prompt prose 里的 casing。
- 分类：prompt/plan 仲裁 bug。
- 合同影响：`/task/AGENTS.md` 已有 `Preserve workbook-visible label text`，但模型仍把 prompt prose casing 看得比 workbook-visible label casing 更强。规则需要明确：如果目标 label 已经作为 workbook header、category、status 或 example 出现，输出 cell 应使用该 workbook-visible token 的精确形式，除非 instruction 明确要求 recase。

`51680`

- 差异只在逗号邻近 label 的空格：
  - golden `Blue, Green , Red Purple`，output `Blue, Green, Red Purple`
  - `G6`, `G13`, `G14` 有类似差异
- 分类：exact text / whitespace normalization bug。
- 合同影响：对 list-join output，如果 source/header token 包含有意义的前后空格，agent 不应该自动美化 spacing。Assertions 至少需要覆盖一行 whitespace-sensitive 的精确字符串。

`230-16`, `177-6`, `203-15`

- 首个差异：
  - `230-16`: timestamp 只差 trailing space。
  - `177-6`: golden 期望 blank，output 是 NBSP。
  - `203-15`: golden 期望 plural label `Transport Allowances`，output 是 singular。
- 分类：exact text / whitespace / label-token bug。
- 合同影响：已有 exact-text warning 方向正确，但还不够可操作。Plan 应要求为 label 和 text output 写一条 copied-token evidence：source cell、target cell、精确 expected stored token，以及是否保留 whitespace。

### 3. 很多语义任务的 assertion gate 仍然有自证倾向

代表性的真实输出 mismatch：

- `22-47`: `F2:H10` 内 checked values 错位或错误，例如 `F4` golden `3`，output `1`。
- `45738`: `L13` golden `0`，output `1160`。
- `43436`: 多个 count cell 错误，例如 `K2` golden `1`，output `2`。
- `49036`: 精度丢失，golden `66.67% WIN RATE`，output `67% WIN RATE`。
- `48969`: boolean 被写成字符串，例如 golden `False`，output `"FALSE"`。
- `54590`: golden 期望值，output 是 `#N/A`。

这些不是 runner failure。它们说明 agent 到达了本地 SaC pass gate，但 assertions 编码的是 agent 自己的解释，而不是能区分对错的 workbook contract。

合同影响：

- Success criteria 可以保持轻量，但 plan/assertion generation 需要增加一个 hard check：每个 high-risk decision 都要写出一个 plausible wrong output，并断言一个会在该错误解释下失败的 row/cell。
- 对 formatting/precision task，plan 必须区分 “nice display” 和 evaluator-facing stored string/value。`49036` 是明确例子：四舍五入成 `67%` 看起来合理，但实际是错的。
- 对 boolean 和 error，assertions 必须检查 stored type/value，而不是 display-compatible text。

### 4. 一些行是 benchmark 数据质量问题，不应该驱动 prompt 变更

例子：

- `269-44`: evaluator 默认使用 `Sheet1`，但 output/golden 都没有这个 sheet。
- `283-32`: `answer_position` 形如 `Sheet3'!A:G,'Sheet4'!A:G`，对当前 evaluator range parser 是 malformed。
- `49300`: quoted sheet name 前面有 leading NBSP。

这些应该作为 data/evaluator issue 单独追踪。为了它们新增 runtime prompt 规则，会把 benchmark-specific workaround 泄漏进 agent 行为，而且不能提升通用 SaC skill 质量。

## 候选改进

### Benchmark `/task/AGENTS.md`

新增或收紧 runtime-only rules：

- 当 workbook 已经以 header、category、status 或 example 的形式包含目标 label 时，精确 workbook token 优先于 prompt prose casing。
- 对 list/string output，除非 instruction 明确要求 trim、normalize 或 reformat text，否则保留 source token whitespace。
- 对不连续 `answer_position`，assertions 必须覆盖每个 window 至少一个 cell，并记录每个 window 的 row anchor。
- 对 high-risk formula 或 summary，assert evaluator-facing final value/string 的精确结果，包括 precision 和 suffix text。

### Canonical skills

不要把 benchmark-specific evaluator 细节放进 canonical skills。适合上提的通用改进是：

- 在 `writing-univer-plans` 中加强 `Contract Decision Evidence`：每个 high-risk decision 都必须包含一个 plausible wrong output，以及一个能拒绝该错误输出的 assertion/probe。
- 在 `test-driven-univer-development` 中强调 exact stored type/value checks，覆盖 text casing、whitespace、boolean、blank、error、percentage precision，以及 formula-cache-sensitive output。

### Evaluator / dataset

单独开修复或追踪项：

- `answer_position` split 支持 quote-aware parsing。
- trim sheet/range token 周围的 leading NBSP。
- trim comma-separated ranges 周围的普通空格。
- 处理 malformed answer positions 和 missing default sheets。

## 下一轮 patch 验证的优先 case

Prompt/skill 变更后，用这些 case 做一个小回归集：

- `50486`: workbook-visible labels 的精确 casing。
- `51680`: list-joined labels 的精确 whitespace。
- `49036`: percentage precision 和 final text。
- `48969`: boolean stored type，而不是 string。
- `45944`: discontiguous answer windows 和 row anchor。
- `130-9`: quoted sheet name data issue，加上真实 header-mapping assertion gap。

