# Claude prompt stdin avoids argv limit

## Baseline

- Related fixed task: `535-20`
- Dataset: `spreadsheetbench_verified_400`
- Prior Codex failure mode: `Argument list too long` from passing a 199 KB `prompt.md` as an argv value.

The same risk existed in the Claude branch of `docker/spreadsheetbench-univer-cli-agent/run-task.sh`:

```bash
prompt="$(cat /task/prompt.md)"
claude -p "$prompt" ...
```

For very wide workbook previews, this can exceed the OS process argument limit before Claude starts.

## Change

Updated the Claude branch to run `claude -p` without a prompt argv and feed `/task/prompt.md` on stdin:

```bash
claude -p ... < /task/prompt.md
```

Claude Code documents `-p/--print` as non-interactive output mode useful for pipes, so stdin is the appropriate transport for large prompts.

## Verification

- Unit test: `python3 -m unittest tests.test_univer_agent_runner.UniverAgentRunnerTest.test_claude_agent_reads_prompt_from_stdin_to_avoid_argument_limit tests.test_univer_agent_runner.UniverAgentRunnerTest.test_codex_agent_reads_prompt_from_stdin_to_avoid_argument_limit`
- Result: passed.
- Shell syntax: `bash -n docker/spreadsheetbench-univer-cli-agent/run-task.sh`
- Result: passed.

Rebuilt the Docker image:

```bash
bash scripts/build_agent_docker.sh
```

Single-task Claude rerun:

```bash
bash scripts/run_univer_agent_eval.sh --agent claude --dataset spreadsheetbench_verified_400 --task-id 535-20 --run-id tmp-claude-verified400-task535-20-stdinprompt-20260525-verify --agent-timeout 300
```

Result:

- Run status: `ok`
- Accuracy: `1.0`
- Total cases: `1`
- Correct cases: `1`
- Error cases: `0`
- Timeout cases: `0`
- Evaluation message: `Cell values in the specified range are identical.`

## Impact

Claude and Codex now both avoid passing large generated prompts through argv. This reduces startup failures on very wide workbook previews without changing prompt content or evaluation logic.
