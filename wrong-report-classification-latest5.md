# 错题分类与最近 5 次通过率

数据源：`wrong-report-matrix.univer` 的 `codex-gpt-5.5-verified400!A1:AI114`，通过 `univer run` + `getCellDatas()` 读取。最近 5 次通过率从最右侧报告列向左取最近 5 个实际 `PASS/FAIL`，跳过 `NOT_RUN`。


## 题目/示例问题，不应该修复（1）
- **44017**：通过率:0/5。原因：golden 与题面/input 不一致：题面明确说基准在 W、frequency 是月间隔，input 中 Semi=6/Quarterly=3；golden 却按 Q:AB 月度旧率列计算，并把 Semi/Quarterly 的缓存值变成 2/4。评测只读 data_only=True 缓存值，导致 AD14:AO42 有 298/348 个等价值差异；不是 CLI/SDK 问题，也不适合通用提示修复。

## 题目/示例数据问题，可尝试通过特定提升词修复，但价值很低（5）

- **22-47**：通过率:1/5。原因：题目一方面要求按 J 列 helper 顺序优先、组内保持源顺序、未列入 J 的保持源顺序，并去空/表头/重复；末句又要求最终输出 G:H 且 sort only column H lowest to highest。agent 识别冲突后选择保留 NAME/REF 行配对和 helper 顺序，没有按 H 升序排。golden 的 F2:H10 实际按 H/REF 数值升序排列，agent 输出按 helper 优先顺序，导致判分范围值不一致。
- **146-49**：通过率:0/5。原因：output 与 golden 在 Sheet1!G1:H65 的 65 行全部不一致，但集合在交换两列后完全一致；agent 输出为 vowelWord, sWord，例如 ALEXINE/ALEXINS，golden 要 sWord, vowelWord，例如 ALEXINS/ALEXINE。初始表 G1:H1 又给了 KAGOULE/KAGOULS 这种 vowelWord, sWord 示例，误导 agent 采用了与 golden 相反的列方向；无 CLI/SDK 异常，耗时 173s，正常导出。
- **32023**：通过率:0/5。原因：题面和 answer_position 都指向 B2:B17，但 golden 实际保留 B2:B3 为空、从员工行 B4 开始写公式，且完整 golden 还写到 B19；最新 output 按题面从 B2:B17 写公式，评测口径下仅 B2/B3 多出 C78，B4:B17 与 golden 一致。根因是题目/标注边界冲突叠加 agent 未优先按可见员工行结构对齐。
- **45738**：通过率:0/5。原因：E6:AB25 按 data_only=True 只差 L13：output=1160，golden=0。L13 对应半年度债券，D13=2023-02-01，L4=2022-08-31；agent 用月末/DATEDIF 口径判断距到期月末 6 个月，应付利息。golden 用 YEARFRAC(L$4,EOMONTH($D13,0))*12 口径，8/31 到 2/28 不算整 6 个月而期望 0；init 里 L13 原值和示例公式区域还支持 1160。
- **56786**：通过率:0/5。原因：golden 在 C4:C200 期望 Table 结构化公式，滚动 365 天平均包含当前行及同日期所有行；agent 根据示例 AVERAGE(B24:B69) 判断为只平均当前行之前的数据，C4 留空、C5 起整体少纳入当前行，导致 197 个判分单元格值均不一致。属于题目/示例与 golden 口径歧义。

## 题目/示例数据问题，可尝试通过特定提升词修复，价值中（4）

- **118-50**：通过率:0/5。原因：题目要求排序 A 列，并在 C/D 输出第五字母移到首位后仍能匹配到词表中单词的词对；初始 C1:D1 示例与列含义/目标起始行有干扰。agent 把所有指定后缀词都机械转换并从 C2 开始输出，只按自生成结果验证。评测按 C2:D5000 比较，golden 实际只有 12 个有效词对写在 C1:D12，因此 C2 起期望 11 行而 output 有 967 行，首格即 RABEAING/ABEARING vs TAVERING/AVERTING。

- **53161**：通过率:1/5。原因：agent 发现直接按 Agent Categories + Agent Schedule 计算会得到小计数，但因下方 EXAMPLE RESULT 与其冲突，选择把 F36:AE43 示例结果复制到 F22:AE29。openpyxl 按评测口径比对，F22:AE29 有 205 个值不一致，例如 F22 output=6、golden=1。golden 使用 SUMPRODUCT 按每个时间段内排班 agent 是否属于 category 计数，示例块明显误导。不是评测或 CLI bug。

## agent理解问题，可尝试通过特定提升词修复（4）
- **469-9（已处理）**：通过率:2/5。原因：题目要求把 Column C 金额拆到 H Debits 和 I Credits，写绝对值，非适用格留空，检查 H1:I10。本次 agent 用 Balance 列反证正负号含义：正数金额后余额下降、负数金额后余额上升，所以判定正数为 debit、负数为 credit；只写 H1:I10。过程仅有 inspect --json 不支持的小卡点，改用 range inspect/run 完成。openpyxl 按评测逻辑对比 output/golden H1:I10 通过；历史失败是 agent 反向理解正负号，本次通过反证检查避免。
- **80-42（已处理）**：通过率:0/5。原因：agent 发现 Consolidate_ALL!A2:L3999 已有 Jack/Henry/Richard 合并数据后，误判为无需追加，只扩展到 8000 行并保持 A4000:L8000 为空；golden 按 first available blank rows 从第 4000 行再次追加同一批源数据到第 7997 行。未见 SDK/CLI 或评测异常，核心是追加语义被理解成去重/已完成检查。
- **49036（已处理）**：通过率:0/5。原因：output 的 Dashboard!B8 是数值 0.6666666666666666 + 自定义格式 0% "WIN RATE"，显示为 67% WIN RATE；golden data_only=True 值是文本 66.67% WIN RATE，公式为 TEXT(...,"0.00%")&" WIN RATE"。题目同时要求不改变 number format，示例又写 67% WIN RATE，还提到 .00 decimal，与 golden 的文本化两位小数目标冲突；不是 CLI/SDK bug。
- **170-13**：通过率:3/5。原因：output/golden 在 Sheet1!A1:A50、Sheet2!A1:E20 完全一致，但 Sheet3!A1:A50 有 49 处值差异。agent 按 Sheet2 表头顺序成组输出，并把现有 Sheet3 示例顺序当成强证据；golden/题意实际要求按 Sheet1 Entry 行顺序逐条匹配并展开到最后一行。运行无超时、导出成功，不是评测程序或 CLI 问题。

## sdk/CLI bug, 因修复问题后再看（6）

- **50193**：通过率:0/5。原因：不是 agent 理解问题。agent 只改 RS.Food!K6:K607，用 SUMPRODUCT+COUNTIFS 按行序打破同值排名，自检样例符合题意。失败根因仍是 sdk/CLI import 后 I 列 IFERROR(INDEX(...MATCH(TRUE,EXACT(...)))) 公式链计算错误：K6:K607 有 465/602 个不一致，同时 A/B 源数据无差异，I 有 475 个不一致、J 有 448 个不一致；典型 output I8/J8/K8=Kids/280/4，golden 为空；output K231=58，golden K231=1。对应 issue #329。
- **54590**：通过率:0/5。原因：确认是外部 workbook 引用公式缓存污染：init/golden 中 GK3:GK20 等外部引用公式有有效 data_only 缓存，golden GK29=692.71486185；run output 中同源公式缓存大量变为 #N/A，GK29 data_only=0。agent 只改 GK29，并在 Univer 可见污染状态下验证为 0。output/golden 均可被 openpyxl 读取，不是当前评测程序读取失败，也不是 issue#317 的条件格式读取问题。
- **33157**：通过率:1/5。原因：runner ok，未超时；仅 K3 关键值不一致：output 空，golden Activity 1。sdk issue#324/import 后 Sheet1!C3 公式计算值为空仍是根因：.univer 中 C3 保留公式但值为 ""，导致 J3 算成 0，agent 信任该状态后把 K3 留空；原始/golden xlsx 的 C3/J3 在 data_only=True 下均为 2009-01-16。
- **41978**：通过率:0/5。原因：agent 在 .univer 内部已正确写入并验证 Cumulative!I2:I11 = 0,0,0,2,0,0,1,26,9,2，golden data_only 同值。失败发生在最终 univer export 后：output.xlsx 中 I2:I11 全为 None，连 B1/G1 也为空，sheet1.xml 为 185 个 row、0 个 cell；init/golden 均为 1849 个 cell。与 issue #320 的 import-export 丢 cell 节点现象一致。
- **59884**：通过率:0/5。原因：根因仍是 sdk issue#330：univer import 后 G2:H5 array formula 计算缓存从 Excel/golden 的 0,0;1,3;2,4;3,5 变成 1,3;2,4;3,5;空,0，agent 基于这个错误可见状态把 a,b,c 写到 I2:K2，导致 I2:O5 相比 golden 整体上移一行。矩阵备注和 issue/59884-array-formula-roundtrip-cache-pollution.md 一致。


## 大小写，单复数，空格，NA，空白，0等(10)
- **5835**：通过率:0/5。原因：golden 在 C3:C19 使用 SUMIFS(I:I,G:G,Bx,H:H,Ax)，data_only=True 下空源值/无匹配应为 0；agent 改写为静态值，并把空源值或无匹配行清成空白，导致 C6:C14、C17 与 golden 不一致。属于空白与 0 语义判断问题。
- **42216**：通过率:3/5。原因：最新 PASS，openpyxl 按 data_only=True 对比 B20:B339 无差异。agent 正确把 April 插入 Group A 后按最终布局解释 answer_position，填充 A20:B339，April/blank 写 0，NA 写文本 NA。历史结构变更 answer_position 修复仍相关，但最近 r1 FAIL 是题面同时说 NA 留空/留 NA，agent 选空白导致少数 NA 不一致。
- **524-31**：通过率:0/5。原因：E1:E53 仅 7 个无匹配交易不一致：output 写入文本 #N/A，golden 在这些格保留 VLOOKUP 公式但 data_only=True 缓存值为 None。题目未说明无匹配项应写空白、错误值还是文本；agent 分类映射本身基本正确，失败主要来自 golden/评测口径对未匹配值的歧义。
- **53383**：通过率:2/5。原因：最新 PASS，openpyxl(data_only=True) 对比 worksheet2!C3:C6 与 golden 完全一致：Matched / Not Matched / Matched / Matched。过程有可恢复 Sheet not found：先误查 worksheet1，随后按实际 sheet 名 worksheet 1 重试成功。历史大小写问题这次不再复现：agent 读取示例 worksheet2!C3:C4，采用 Matched/Not Matched，而不是题面小写 matched/not matched。
- **54667**：通过率:0/5。原因：最新 run 执行 OK、评测 FAIL。agent 额外加入 E<>"" 防空白匹配，导致 G6:G58 导出为空；golden 公式无该 guard，空白 D=E 时返回空 M 并缓存为 0:00。目标区无动态数组/FILTER，导出成功且非空样本缓存正常，不是 SDK/CLI 导出问题。
- **203-15**：通过率:4/5。原因：题干列举 allowance 为单数，但源数据/golden 使用 Transport/Other/Social Allowances 复数；历史失败来自 agent 按题干归一化。最新 run 保留源 H 列原文，Output Required!A1:M3 按 data_only=True 与 golden 完全一致；日志命令均成功，161.63s 完成，无 CLI/API 过程问题。
- **48983**：通过率:4/5。原因：最新 PASS；openpyxl 对比 M6:S11 的 data_only=True 与公式均和 golden 一致。历史失败形态仍相关：早期 agent 过度解释空白源格，给 INDEX/MATCH 加 IF/IFERROR 包装，把源空白返回值从裸公式的 0 改成空白；最新日志明确不加 wrapper，M6 等空白源格按裸 INDEX/MATCH 返回 0，因此通过。不是评测/数据集问题，也不是 CLI bug。
- **51680**：通过率:4/5。原因：最新 PASS，openpyxl 按 data_only=True 比 G2:G14 与 golden 全部一致。历史问题是 agent 曾把表头 C1="Green " trim 成 "Green"，导致拼接文本少尾随空格；本次日志明确检查 C1 JSON 值并保留尾随空格，G3/G6/G13/G14 均写成 Green , ...。未见命令误用、导出失败、越界、缺依赖或超时；output 静态字符串 vs golden 公式不影响评测。
- **230-16**：通过率:5/5。原因：最新 run 评测通过，openpyxl 对比 output/golden 的 Before!A1:A12 全部一致。历史失败点是拆分文本时把 event_type="BUSINESS" 前的分隔空格留在 A 列，golden 期望删除分隔空格；本次 agent 明确把边界空格当 delimiter 删除，A2:A9 写纯时间戳，B2:B9 写 event_type="BUSINESS"。不是 CLI/SDK 或评测问题。
- **55427**：通过率:5/5。原因：最新 PASS，openpyxl(data_only=True) 对 Compiled and located schools da!B2:B1461 比 output/golden 差异为 0；输出包含 1312 个数字、106 个 #N/A、42 个空白，和 golden 一致。agent 正确识别 L 邮编有前导空格，使用 MATCH(TRIM(Lrow),...)，只填 B2:B1419，保留 B1420:B1461 为空。历史 #N/A vs 空仍是有效根因，但最新没有 IF(TRIM(L)="","",...) 包装，B160 已为 #N/A。