---
name: Foreground shell rule
overview: Add one always-on PlasticOS rule so long agent commands stay attached until
  they finish. Cursor’s running agent host still sends SIGTERM when a command is handed
  to the background, and editing the app bundle does not change that host.
todos:
- id: add-foreground-rule
  content: Add always-apply .cursor/rules/37-plasticos-foreground-shell.mdc with the
    10-minute attached wait and the one-command rule
  status: completed
isProject: false
built: true
status: built
---

# Foreground long agent commands

The measured failure is the handoff, not Docker or `make`. A 2-second wait on a 4.5-second probe received `SIGTERM` at 2085 ms and the terminal ended `aborted`. The same host kills an immediate background (`block_until_ms: 0`) in about 110–130 ms. A wait longer than the command does not hand off: `make test-module` and `make pr` both finished when the wait was 10 minutes. The on-disk edit to `cursor-agent-exec` was restored because the running host never loaded it.

## Already wired

`make pr` already runs `install-smoke`, and `make test-module` / `make test-odoo` already call [`scripts/test_env.sh`](scripts/test_env.sh) against [`config/test_env_fixture.conf`](config/test_env_fixture.conf). The integration-testing adapter already says the same thing: when that fixture file exists, the procedure is `scripts/test_env.sh` `clone` and `run` on the host compose stack, and the container quick path is blocked. Neither the Makefile nor the skill chooses the agent wait. That wait is set on the shell the agent starts, before `make` or the skill runs. Do not edit the skill or the Makefile for this.

The rule is what lets those existing calls reach Docker. A backgrounded `make pr` or `make test-module` dies in about 110 ms, before the fixture script starts.

## Change

Add [`.cursor/rules/37-plasticos-foreground-shell.mdc`](.cursor/rules/37-plasticos-foreground-shell.mdc) with `alwaysApply: true`, next to the existing fixture rule [`36-plasticos-docker-test-fixture.mdc`](.cursor/rules/36-plasticos-docker-test-fixture.mdc). No module version bump, no `AGENTS.md` edit, no change under `/Applications/Cursor.app`, no change to `l9-pr-integration-testing` or the Makefile.

The rule tells every agent in this repo:

- Run `make test-module`, `make test-odoo`, `make install-smoke`, `make test-env-rebuild`, `make update`, `make pr`, `make pr-check`, and `git push` attached. Set the wait to **600000** ms (10 minutes).
- Do not set the wait to **0**, and do not set it shorter than the command. A short wait still hands the process off and the host kills it.
- Run one of those commands at a time. Do not start a second copy while the first is running or showing `Terminated: 15`.
- Short commands (`git status`, a single-file `ruff` check) keep the normal wait.

## Check

- The new file has `alwaysApply: true` and names those commands and the 10-minute wait.
- No `plasticos_*` manifest version changes.
- Do not publish unless you ask. The rule is editor guidance, not a module upgrade.

## Build evidence (auto)

- detected_at: `2026-11-05T15:15:43Z`
- conversation_id: `f28a72fd-1e5a-4f18-abf2-ff9fe741d94c`
- generation_id: `0e178835-998a-4ea8-8f95-ff501ddaca72`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/f28a72fd-1e5a-4f18-abf2-ff9fe741d94c/f28a72fd-1e5a-4f18-abf2-ff9fe741d94c.jsonl`
- todos at build time:
- `add-foreground-rule`: completed
