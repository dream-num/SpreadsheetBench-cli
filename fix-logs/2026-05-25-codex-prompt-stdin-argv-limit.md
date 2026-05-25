# Codex prompt stdin avoids argv limit

## Baseline

- Dataset: `spreadsheetbench_verified_400`
- Baseline run-id: `codex-gpt-5-5-verified400-all-20260523-230050`
- Task: `535-20`
- Baseline result: runner error, no output file
- Baseline error:

```text
/usr/local/bin/spreadsheetbench-agent-task: line 63: /usr/local/bin/codex: Argument list too long
```

The generated `prompt.md` for this task was about 199 KB because the workbook preview included a very wide first row. The container script read the prompt into a shell variable and passed it as the final `codex exec` argument, which exceeded the process argument limit before Codex could start.

## Change

Updated `docker/spreadsheetbench-univer-cli-agent/run-task.sh` so the Codex branch invokes:

```bash
codex ... exec ... - < /task/prompt.md
```

Codex documents `-` as reading the initial instructions from stdin, so the prompt no longer travels through argv. The Claude branch still reads `prompt.md` into `-p` only inside the Claude branch.

## Verification

- Unit test: `python3 -m unittest tests.test_univer_agent_runner.UniverAgentRunnerTest.test_codex_agent_reads_prompt_from_stdin_to_avoid_argument_limit tests.test_univer_agent_runner.UniverAgentRunnerTest.test_codex_agent_can_bypass_nested_sandbox_inside_docker`
- Result: passed.

Rebuilt the Docker image:

```bash
bash scripts/build_agent_docker.sh
```

Single-task rerun:

```bash
bash scripts/run_univer_agent_eval.sh --agent codex --dataset spreadsheetbench_verified_400 --task-id 535-20 --run-id tmp-codex-verified400-task535-20-stdinprompt-20260525-verify --agent-timeout 300
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

This fixes Codex task startup for very large prompts generated from wide workbook previews. It does not change prompt content or scoring logic.

## Remaining Risks

- Claude still receives the prompt through `claude -p "$prompt"` and may have the same argv-limit risk on similarly large prompts.
- Very large prompts can still be expensive for the model even though process startup now succeeds.
