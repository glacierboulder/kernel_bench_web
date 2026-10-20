# DSH integration review

Reviewed official repository and downloaded npm release archives, 2026-10-09 (Hong Kong).

## Selected distribution

Prefer project-local npm `@deepseek-ai/dsh@0.2.0-rc.2`, exact version plus package-lock.
Do not use unversioned `npx` for experiments. Source master currently advertises
0.2.1-alpha.1 and requires pnpm/build/native development dependencies, making it
less suitable for a first server integration. Source archives downloaded for
inspection are not installed runtimes.

Installation requires user confirmation under the user-provided AGENTS.md.
No dependency installation has been performed at the time of this review.

## Verified release protocol

`node <runtime>/node_modules/@deepseek-ai/dsh/lib/bin.js --profile headless --patch <trusted-overlay.yml> --json -`

- Input: task text on stdin, verbatim.
- stdout: JSONL `session`, `status`, `text`, `thinking`, `tool_call`, `tool_result`, `final` (or `error`).
- `session.sessionId`: checkpoint immediately; recovery uses `--session-id` with the same cwd and persistent DSH_HOME.
- Exit 0: completed turn; exit 1: abort/error. `final` alone is not proof of success.
- Non-final event payloads can be truncated. Keep the raw event archive and truncation flags.
- `status.phase=step_end` may include provider token usage. No invented cost conversion.
- `--model` and `--max-turns` are not public headless flags. Model is selected through the trusted `agent-default-model` patch row.
- `DSH_HOME`: dedicated per-run state, never the user's real home.
- Published provider uses **Anthropic Messages**, public base `https://api.deepseek.com/anthropic`, not OpenAI Chat Completions.
- Provider route: `deepseek-official`; API key reference defaults to DEEPSEEK_API_KEY.
- `DEEPSEEK_BASE_URL` or provider `baseURL` controls the endpoint.
- Outer sandbox must enforce filesystem and network restrictions. DSH permission mode is not a host boundary.

## First task scope

Only `tasks/task_single` may enter the agent workspace. No private evaluator,
upstream git history, or host home is mounted. Agent may modify a disposable
source copy and provide a report; supervisor materializes the diff against the
frozen baseline. Evaluator runs separately without model access. All code
compilation and execution must also remain within an outer sandbox.

Sources:
- https://github.com/deepseek-ai/deepseek-harness
- https://github.com/deepseek-ai/deepseek-harness/blob/master/SAFETY.md
- npm release archives in `research/packages/`, metadata includes shasums/integrity.
