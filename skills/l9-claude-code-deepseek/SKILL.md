---
name: l9-claude-code-deepseek
description: bring Claude Code CLI up through the shared installer Web already uses, and confirm the DeepSeek route is present. use when a Claude Code CLI session should load the same bootstrap as Claude Code Web.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, claude-code, deepseek, bootstrap]
  owner: igor_beylin
  status: active
  version: 2.0.0
  updated: 2026-11-21
---

# l9-claude-code-deepseek

Bring Claude Code CLI up through the installer Claude Code Web already uses. Confirm the DeepSeek route. Never print a key, and never write one.

Identity and projection admission come from the `Quantum-L9/.github` checkout at `~/.l9/authority/.github`. Do not name a consumer repository.

## Do

1. From `~/.cursor-governance`, run `make claude-install WS=<workspace>`. That is the CLI caller of `environment/agents/adapters/claude-code/install.sh`, the same installer Web reaches through `web/setup.bootstrap.sh` → `web/setup.sh`. Do not restate installer steps.
2. Confirm `DEEPSEEK_API_KEY` with `l9-secrets`: `"$PY" "$SECRETS/capability_bind.py" --check DEEPSEEK_API_KEY`. The legacy ref `openclaw-igorbot/deepseek#apikey` checks the same name. Presence and source only. Follow `l9-secrets` for the interpreter. Do not bind the value into a file, the shell, or chat.
3. If CLI lacks something Web has, add it to `install.sh` or `ops/scripts/bootstrap_agent_environment.sh`. Do not grow a CLI-only path in this skill.

## Do not

- Write `.env`, `.env.local`, a wrapper, `.claude/settings.local.json`, or `claudeCode.environmentVariables`.
- Install the Cursor extension, set `claudeCode.claudeProcessWrapper`, or edit `~/.claude.json`.
- Run or copy `$HOME/.cursor-governance/scripts/claude-deepseek.sh`.
- Put `ANTHROPIC_BASE_URL` or a token into `settings.template.json` or `web/environment.env.example` from this skill. A later edit to the template `env` object is how both surfaces switch together.

## Pass

- `~/.l9/claude/bootstrap-state.json` reports the required plane `READY`.
- `L9_GOVERNANCE_SURFACE` is `claude-code`.
- `/status` shows `https://api.deepseek.com/anthropic` and `deepseek-v4-pro[1m]`. The token is not `sk-ant…`.

If the route is absent, report that gap. Do not fill it with a file.

## Fail

- Bare `claude`.
- `$HOME/.cursor-governance/scripts/claude-deepseek.sh`, or a clone copy of that script.
- A key in chat, git, or tracked settings.
