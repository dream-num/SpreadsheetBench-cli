# 56427: 题面不完整 hex 色值导致导出非法 OOXML 颜色

- Upstream issue: https://github.com/dream-num/univer-cli/issues/364

## 现象

任务 `56427` 的题面要求把 `H2:S28` 填充为 `#E2EFD`。该值不是合法的 Excel/CSS hex 颜色：`#` 后只有 5 位十六进制字符。

在失败 run `codex-gpt-5-5-verified400-all-20260527-220546` 和 `codex-gpt-5-5-verified400-allwrong96-workflowplan-w15-timeout480-20260528-152629` 中，agent 直接调用：

```ts
target.setBackgroundColor('#E2EFD');
```

`univer run` 接受该值，`getBackgrounds()` 也回读为 `#E2EFD`，但 `univer export` 生成的 `xl/styles.xml` 中出现：

```xml
<fgColor rgb="FFE2EFD"/>
```

这是 7 位 ARGB 值，严格 OOXML 读取器无法解析。`openpyxl.load_workbook(..., data_only=True)` 报错：

```text
ValueError: Unable to read workbook: could not read stylesheet ...
```

后续复测发现更细的工具链问题：即使 agent 先写入非法 `#E2EFD` 后又把同一范围改成合法 `#E2EFDA`，导出的 `xl/styles.xml` 仍会保留此前的非法 fill。该 fill 可以已经不被任何 cell xf 引用，但只要存在于 stylesheet 中，openpyxl 仍会拒绝读取整个 workbook。

## 最小复现

在本地 CLI 中可用空 workbook 复现：

```bash
univer new debug-tmp/color-hex-repro/invalid-color.univer --name InvalidColorRepro --json
univer run debug-tmp/color-hex-repro/invalid-color.univer --code "() => { const sheet = univerAPI.getActiveWorkbook().getActiveSheet(); sheet.getRange('A1').setValue({ v: 'x', t: 1 }); sheet.getRange('A1').setBackgroundColor('#E2EFD'); return { background: sheet.getRange('A1').getBackground() }; }"
univer export debug-tmp/color-hex-repro/invalid-color.univer debug-tmp/color-hex-repro/invalid-color.xlsx --json
python3 - <<'PY'
from openpyxl import load_workbook
load_workbook('debug-tmp/color-hex-repro/invalid-color.xlsx', data_only=True)
PY
```

结果：导出的 `styles.xml` 含 `rgb="FFE2EFD"`，openpyxl 读取 stylesheet 失败。

二次修复残留复现方向：

```js
sheet.getRange('A1').setBackgroundColor('#E2EFD');
sheet.getRange('A1').setBackgroundColor('#E2EFDA');
```

随后导出 xlsx，检查 `xl/styles.xml`，仍可能看到残留的 `rgb="FFE2EFD"`，并导致 openpyxl 读取失败。

## 正确用法线索

- `/Users/otime/project/univer/packages/core/src/types/interfaces/i-style-data.ts` 中 `IColorStyle.rgb` 注释为 `#RRGGBB` 或 `rgb(r, g, b)`。
- `/Users/otime/project/univer/packages/sheets/src/facade/f-range.ts` 的 `setBackgroundColor(color: string)` 当前只是把 `color` 存到 `{ rgb: color }`，没有校验。
- `/Users/otime/project/univer-cli/apps/cli/src/run-help/topics/formatting.md` 的示例使用完整 6 位 hex：`#F2F2F2`。
- 历史通过 run 多数把该任务颜色写为 `#E2EFDA`；例如 `codex-gpt-5-5-verified400-all-20260525-153934` 的脚本明确备注题面 `#E2EFD` 似乎缺少最后一位，并使用 `#E2EFDA`。

## 归因

这是两个问题叠加：

1. 题面色值有歧义：`#E2EFD` 不是合法 hex 颜色，疑似缺少最后一位。
2. CLI/API 未校验传入的颜色字符串：`setBackgroundColor('#E2EFD')` 成功写入 workbook 状态，导出时生成非法 OOXML 色值，导致评测的 openpyxl 读取阶段失败。
3. 非法颜色进入样式表后，后续把可见单元格改成合法颜色不能可靠清理旧非法 fill；因此二次 `setBackgroundColor('#E2EFDA')` 不是安全修复路径。

## 当前规避方向

不在本轮修复 CLI/API。先通过 agent prompt 规避：

- 对所有传给 `setBackgroundColor()`、`setBackground()`、`setFontColor()`、rich text `cl/bg`、条件格式颜色等 facade/API 的颜色做合法性检查。
- Excel/xlsx 兼容场景优先使用完整 `#RRGGBB`，或明确合法的 `rgb(r, g, b)`；不要直接传入命名色、5 位/7 位 hex、少写或多写的 `#` hex。
- 如果题面给出不完整 hex，先从 workbook 示例样式、题面上下文或常见 Excel 颜色判断意图；只有意图清楚时才改成合法 6 位 hex，并在 implementation plan 中写明该假设。
- 写颜色前必须先校验；如果已经把非法颜色传入 workbook，不能靠再次设置合法颜色修补，应 `univer restore <input.univer>` 回到干净状态后重做所有编辑。
- 验证时不能只看 `getBackgrounds()` 是否等于输入字符串；还要确认最终传入和回读的颜色满足合法格式，并在需要时检查导出的 `.xlsx` 能被 openpyxl 读取。

## Prompt 规避验证

已在 `inference/univer_agent/prompts.py` 增加通用提示：写入任何颜色 API 前先验证颜色字符串；如果误写非法颜色，必须 restore 干净 workbook 后重做，不要二次覆盖修补。

单题重跑验证：

- `tmp-codex-gpt-5-5-verified400-56427-colorprompt-escalated-20260531-160229`：PASS，日志中先识别 `#E2EFD` 非法并写入 `#E2EFDA`，导出 xlsx 无 `rgb="FFE2EFD"`。
- `tmp-codex-gpt-5-5-verified400-56427-colorprompt-rerun2-20260531-161521`：PASS，日志中明确 “never pass malformed `#E2EFD` to the workbook”，实际脚本直接 `setBackgroundColor("#E2EFDA")`，导出 xlsx 无 `rgb="FFE2EFD"`。

后续通用修复仍应考虑在 `univer-cli` 或上游 facade/export 边界拒绝非法颜色，避免生成不可读 `.xlsx`。
