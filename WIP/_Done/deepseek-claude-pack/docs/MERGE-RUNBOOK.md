# Merge runbook — DeepSeek × Claude Code (PR #121)

For the agent merging https://github.com/Quantum-L9/Cursor-Governance/pull/121
into `Quantum-L9/Cursor-Governance` `main`.

This PR only adds env-routed Claude Code launchers, a secrets-registry **ref**,
and this pack. It does **not** change model routing for Cursor Agent.

## Non-negotiable

1. Never print, commit, or paste `DEEPSEEK_API_KEY` / `ANTHROPIC_AUTH_TOKEN`.
2. Never write the key into `.claude/settings.json` or CI YAML.
3. Never force-push, `--admin` merge, or `git reset --hard`.
4. Do not merge from the dirty `main` checkout that still has unrelated WIP
   (`l9-mac-storage-triage`, settings/autonomy dirt). Use this PR branch or a
   clean worktree.
5. Resolve GitHub with `openclaw-igorbot/github#token`. Do not ask the human
   to click `github.com`.
6. Older open PRs (earlier `createdAt`) merge **bottom-up first**.

## What already shipped (do not redo)

| Piece | State |
|---|---|
| AWS secret `openclaw-igorbot/deepseek` JSON key `apikey` | Provisioned `us-east-1` |
| Registry ref `openclaw-igorbot/deepseek#apikey` | In this PR |
| Launchers `scripts/claude-deepseek.sh` / `.ps1` | In this PR |
| Pack under `WIP/deepseek-claude-pack/` | In this PR |
| Pre-merge e2e (2026-08-13) | Claude Code `-p` returned `pong` via `api.deepseek.com`, not `api.anthropic.com` |

## 0. Identity and token

```bash
REPO="${HOME}/Cursor-Governance/Cursor-Governance-deepseek"
# or: git fetch origin feat/claude-code-deepseek-v4 && git worktree add /tmp/cg-121 origin/feat/claude-code-deepseek-v4
cd "$REPO"
PY="${HOME}/.cursor-governance/.venv/bin/python"
[ -x "$PY" ] || PY=python3

# check only — must print OK, never a value
"$PY" ops/secrets/resolve_secret.py --ref 'openclaw-igorbot/deepseek#apikey' --check
"$PY" ops/secrets/resolve_secret.py --ref 'openclaw-igorbot/github#token' --check

GH_TOKEN="$("$PY" ops/secrets/resolve_secret.py --ref 'openclaw-igorbot/github#token')"
export GH_TOKEN GITHUB_TOKEN="$GH_TOKEN"
```

## 1. Older PRs first

```bash
gh pr list --repo Quantum-L9/Cursor-Governance --state open \
  --json number,title,createdAt,mergeable,url \
  --jq 'sort_by(.createdAt) | .[]'
```

As of open: **#119** (`WIP: 26CR case work without media`, created earlier)
then **#121**. If #119 is still open, remediate and merge it first (or get an
explicit human exception). Do not merge #121 onto a tip that will force a
rebase of an older live PR.

## 2. Confirm #121 is still this change-set

```bash
gh pr view 121 --repo Quantum-L9/Cursor-Governance \
  --json title,baseRefName,headRefName,mergeable,mergeStateStatus,statusCheckRollup,url
git log --oneline origin/main..origin/feat/claude-code-deepseek-v4
git diff --name-only origin/main...origin/feat/claude-code-deepseek-v4
```

Expect only DeepSeek pack / launchers / `.gitignore` / Makefile targets /
`ops/secrets/openclaw-igorbot.registry.yaml`. If unrelated files appeared, stop.

Required checks must be green. Re-run failed required checks; do not bypass.

## 3. Re-run e2e on the PR tip (required before merge)

Hydrate `.env.local` from AWS if the placeholder is still there. Do not echo
the value.

```bash
cd "$REPO"
"$PY" - <<'PY'
from pathlib import Path
import subprocess
env = Path(".env.local")
if not env.is_file():
    env.write_text(Path("WIP/deepseek-claude-pack/env.local.example").read_text())
text = env.read_text().splitlines()
key = subprocess.check_output(
    [str(Path.home() / ".cursor-governance/.venv/bin/python"),
     "ops/secrets/resolve_secret.py",
     "--ref", "openclaw-igorbot/deepseek#apikey"],
    text=True,
).strip()
out = []
found = False
for line in text:
    if line.startswith("DEEPSEEK_API_KEY="):
        out.append("DEEPSEEK_API_KEY=" + key)
        found = True
    else:
        out.append(line)
if not found:
    out.append("DEEPSEEK_API_KEY=" + key)
env.write_text("\n".join(out) + "\n")
print("wrote .env.local key_chars=%d (value not printed)" % len(key))
PY

./scripts/verify-routing.sh
./scripts/claude-deepseek.sh \
  -p "Reply with the single word pong and nothing else." \
  --output-format json \
  --no-session-persistence \
  --permission-mode dontAsk \
  --tools ""
```

Pass bar:

- `verify-routing.sh` exits 0
- JSON `is_error` is false and `result` is `pong` (or equivalent one-word pong)
- Process env used `ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic`
- `ANTHROPIC_API_KEY` unset; `ANTHROPIC_AUTH_TOKEN` set from the DeepSeek key
- Debug/host evidence must mention `api.deepseek.com` and must **not** show
  `api.anthropic.com` as the request host

If the header/badge would show Claude Max in an interactive session, run
`claude logout` and retry the launcher. See `docs/TROUBLESHOOTING.md`.

Do **not** merge if this e2e fails.

## 4. Merge

Ordinary merge only. Authorization: this stack was requested, e2e-confirmed,
and opened as #121. Set a reason string (not a secret):

```bash
export L9_MERGE_AUTHORIZED="PR 121 DeepSeek Claude Code e2e confirmed; merge after older PRs"
gh pr merge 121 --repo Quantum-L9/Cursor-Governance --merge --delete-branch
```

Forbidden: `--admin`, `--rebase` onto a rewritten history, `git push --force`,
squash if CODEOWNERS/history for this repo requires merge commits (use
`--merge` unless repo settings say otherwise).

## 5. Post-merge activation on `main`

Do this on a **clean** `main` (ff-only pull). Do not drag unrelated dirty files
from the other checkout.

```bash
git fetch origin main
git checkout main
git merge --ff-only origin/main

# local secret file — gitignored
test -f .env.local || cp WIP/deepseek-claude-pack/env.local.example .env.local
# hydrate DEEPSEEK_API_KEY from openclaw-igorbot/deepseek#apikey (same script as §3)

./scripts/verify-routing.sh
# daily launch:
#   ./scripts/claude-deepseek.sh
#   make claude-deepseek
```

Copy `WIP/deepseek-claude-pack/.cursor/rules/claude-code-deepseek.mdc` into
the workspace `.cursor/rules/` if you want the always-on reminder. In this
SSOT clone `/.cursor/` is gitignored, so that copy is local-only.

Cursor Agent is unchanged. Only the `claude` process started by the launcher
is DeepSeek-routed.

## 6. Rollback

```bash
gh pr revert 121 --repo Quantum-L9/Cursor-Governance
# or: git revert <merge-commit> && make pr
```

Then launch bare `claude` (Anthropic). Leave the AWS secret in place; it is
harmless if unused. Do not delete `openclaw-igorbot/deepseek` unless a human
asks.

## 7. Failure table

| Symptom | Action |
|---|---|
| `UNREGISTERED` / `NOT_FOUND` on deepseek ref | Stop. Secret must exist in AWS + registry. Do not invent a second secret. |
| 401 from Claude Code | Unset `ANTHROPIC_API_KEY`; use `ANTHROPIC_AUTH_TOKEN` only |
| Session bills Anthropic | You launched bare `claude` |
| merge_gate denies `gh pr merge` | Set `L9_MERGE_AUTHORIZED` as in §4, or a valid L4 release receipt |
| Older PR still open | Merge that PR first (bottom-up) |
| Dirty unrelated files on `main` | Work in a clean worktree; do not commit them onto #121 |

## Pointers

- Pack README: `WIP/deepseek-claude-pack/README.md`
- Troubleshooting: `WIP/deepseek-claude-pack/docs/TROUBLESHOOTING.md`
- Mobile: `WIP/deepseek-claude-pack/docs/MOBILE.md`
- Secret skill: `l9-aws-secrets` — ref `openclaw-igorbot/deepseek#apikey`
- Merge gate: `ops/autonomy/merge_gate.py`
