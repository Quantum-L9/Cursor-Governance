---
name: l9-claude-code-deepseek
description: wire Claude Code in a consumer clone to DeepSeek (not Anthropic billing). use when opening Claude Code in a new Cursor tab, hydrating DEEPSEEK_API_KEY, or repeating the Website-Bot DeepSeek setup in another repo.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, claude-code, deepseek, cursor, env]
  owner: igor_beylin
  status: active
  version: 1.0.0
  updated: 2026-08-14
---

# l9-claude-code-deepseek

Route Claude Code in **this clone** to DeepSeek. Never print key values.

## Do

1. `cursor --install-extension anthropic.claude-code` if missing.
2. Resolve `openclaw-igorbot/deepseek#apikey` via `l9-aws-secrets` (`--check` first). Write gitignored `<clone>/.env.local` (`0600`) with DeepSeek exports. Add `.env.local` and `.claude/settings.local.json` to the clone `.gitignore` first.
3. Write **clone-local** `scripts/claude-deepseek.sh` that sources `<clone>/.env.local`, `unset ANTHROPIC_API_KEY`, `cd`s to the clone, `exec claude "$@"`. Do **not** run `$HOME/.cursor-governance/scripts/claude-deepseek.sh` from a consumer — it `cd`s into governance.
4. Set Cursor workspace + user `claudeCode.claudeProcessWrapper` to that script, `preferredLocation=panel`, `disableLoginPrompt=true`. Non-secret DeepSeek URL/models only in settings.
5. Gitignored `.claude/settings.local.json`: same URL/models + `ANTHROPIC_AUTH_TOKEN` from `.env.local`. Never put the key in committed `.claude/settings.json`.
6. Trust the clone in `~/.claude.json` → `projects[<clone>].hasTrustDialogAccepted=true`.
7. Operator: `Cmd+Shift+P` → **Claude Code: Open in New Tab**, then `/status`.

## Pass

`/status` shows `https://api.deepseek.com/anthropic` and `deepseek-v4-pro[1m]`. Token is not `sk-ant…`.

## Fail

- Bare `claude` or the governance wrapper from a consumer clone.
- `ANTHROPIC_API_KEY` still set (Anthropic billing).
- Key in chat, git, or tracked settings.
