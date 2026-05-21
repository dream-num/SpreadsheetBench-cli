# spreadsheetbench-univer-cli-agent

This image is the black-box solver environment for SpreadsheetBench Univer agent runs.

Build:

```bash
bash scripts/build_agent_docker.sh
```

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

Authentication is provided at runtime with `docker run --env-file`; secrets are not baked into the image and are not copied into `/task`.

The image intentionally does not include Python or workbook parsing libraries. Agents should use the installed Univer CLI tooling inside `/task`.
