# SaC adopted workspace apply reports generated artifact path requirement

## 现象

在 `univer sac init <workspace> --from <input.univer>` 创建 adopted workspace 后，`sac.config.ts` 正确写入：

```ts
artifacts: {
  mode: "adopted",
  defaultWorkbook: "../../cases/case_1/input.univer"
}
```

但执行 `univer sac apply <workspace>` 失败：

```text
ERROR SAC_ARTIFACT_PATH_INVALID

SaC generated result artifact must be written to <workspace>/artifacts/<workspace>.univer: <input.univer>
```

显式传 `--target <input.univer>` 也复现同一错误。

## 复现来源

- SpreadsheetBench worktree: `.worktree/sac-univer-cli-runner-20260526`
- run-id: `sac-codex-gpt-5-5-verified400-task13-1-20260526-120715`
- task-id: `13-1`
- image: `spreadsheetbench-univer-cli-agent-sac`
- local `univer-cli` source: `/Users/otime/project/univer-cli` at `32031b12`

关键路径：

```text
.runs/univer-agent/sac-codex-gpt-5-5-verified400-task13-1-20260526-120715/13-1/task/work/sac-case_1/sac.config.ts
.runs/univer-agent/sac-codex-gpt-5-5-verified400-task13-1-20260526-120715/13-1/task/logs/sac-fallback-case_1.txt
```

## 影响

agent 能够完成 SaC 初始化、`pnpm install`、migration create 和 migration authoring，但 adopted artifact apply 被拒绝，最终只能 fallback 到 direct `univer run`。

该 run 的最终 SpreadsheetBench evaluation 通过，说明失败点不在任务推理，而在 SaC adopted apply 路径校验。

后续 prompt 已改为强制 SaC：不再允许 direct `univer run` 作为写入 fallback。遇到该错误时只能继续用 SaC managed generated artifact 路径恢复；如果 SaC 不能产出 artifact，则任务失败。

## 后续建议

在 `univer-cli` 仓库内用最小 `.univer` fixture 复现：

1. `univer sac init ./model --from ./input.univer`
2. `cd model && pnpm install && cd ..`
3. `univer sac migration create "Edit" --workspace ./model`
4. 添加一个最小 sheet migration
5. `univer sac apply ./model`

预期 adopted mode 应写回 `sac.config.ts` 中记录的原始 artifact；实际却按 generated workspace 规则要求 `artifacts/<workspace>.univer`。
