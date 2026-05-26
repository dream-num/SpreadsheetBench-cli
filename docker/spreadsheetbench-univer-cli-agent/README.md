# spreadsheetbench-univer-cli-agent

This image is the black-box solver environment for SpreadsheetBench Univer agent runs.

Build:

```bash
bash scripts/build_agent_docker.sh
```

Build with a local `/Users/otime/project/univer-cli` checkout instead of `univer-cli@latest`:

```bash
bash scripts/build_agent_docker_from_local_univer_cli.sh
```

Use a different local checkout or image tag:

```bash
bash scripts/build_agent_docker_from_local_univer_cli.sh \
  --repo /path/to/univer-cli \
  --tag spreadsheetbench-univer-cli-agent
```

For SaC experiments, use a separate tag:

```bash
bash scripts/build_agent_docker_from_local_univer_cli.sh \
  --repo /Users/otime/project/univer-cli \
  --tag spreadsheetbench-univer-cli-agent-sac
```

This local build script runs `pnpm build` in the checkout, packs `apps/cli/dist`,
installs that tarball into the solver image, then runs the same CLI warmup and
stops both `univer view` and `univer daemon` before the image layer is finalized.

The host runner mounts exactly one task directory at `/task`:

```text
/task
  prompt.md
  cases/case_1/input.xlsx
  outputs/case_1/
  logs/
  work/
```

The container must write:

```text
/task/outputs/case_N/output.xlsx
```

Agent configuration is provided at runtime by read-only mounts. For Codex, mount auth and config files to `/home/node/.codex/auth.json` and `/home/node/.codex/config.toml`. For Claude, mount settings to `/home/node/.claude/settings.json`. Secrets are not baked into the image and are not copied into `/task`.

The image intentionally does not include Python or workbook parsing libraries. Agents should use the installed Univer CLI tooling inside `/task`.
