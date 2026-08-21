# CLAUDE.md — authority pointer

This file exists to be **loaded**, not to be comprehensive. It is deliberately
short so it always fits, and it duplicates no doctrine: it says where doctrine
lives and what outranks what.

A mobile bootstrap audit measured `memory_files_completed {"file_count": 0}` for
a session working in this repository. `CANONICAL_LAW.md` (35 KB) and `AGENTS.md`
(28 KB) were both present on disk and neither reached the model's context, so
the authority chain below was in force and invisible at the same time.

## Authority chain

Highest first. A lower rung never overrides a higher one.

1. **`CANONICAL_LAW.md`** — the constitution. Read it before proposing a change
   to governance, memory, the publish path, or the secret plane.
2. **Autonomy Surface Profile** — `ops/autonomy/surface_profile.yaml`. Matches on
   the exact surface id `claude-code`; a variant id silently drops the session
   out of its standing authority.
3. **`AGENTS.md`** — operating instructions for agents in this repository.
4. **`skills/l9-*`** — task-scoped procedures, invoked by name.
5. **Agent-invented contracts** — none. If you find yourself designing a rule,
   it belongs in one of the four rungs above, in a PR.

## The three things most often got wrong here

- **`make pr` is the sanctioned route to GitHub — and nothing blocks the
  alternatives.** Raw `git push` is *not* denied by
  `ops/autonomy/local_execution_gate.py`; git and gh are exempt from the
  workflow plane and answer to `ops/autonomy/git_guardrails.py`, which denies by
  effect (CANONICAL_LAW §6.2.4). Prefer `make pr` because it runs the checkers,
  not because pushing errors — it will not. What *is* denied at every phase:
  `make push` and the MCP `create_pull_request` / `push_files` tools. If
  `make pr` is what is denied, that is a fault.
- **This surface holds no credentials.** It is `model-controlled`: no Infisical
  import, no PAT, no bearer. Capabilities resolve through the broker, which
  keeps the credential on the far side. A capability reporting `DEGRADED` or
  `BLOCKED_BY_PLATFORM` is never a reason to paste a secret — see
  `docs/DEGRADED_MODE_CONTRACT.md`.
- **Receipts expire.** `~/.l9/claude/bootstrap-state.json` and
  `~/.l9/claude/gov-refresh.json` carry a UTC timestamp and a TTL. Read them
  through `ops/scripts/claude_bootstrap_receipt.py` and
  `ops/scripts/governance_refresh_receipt.py`, which recompute state rather than
  trusting the recorded word. An absent receipt means `never_ran`, not `ready`.

## Checking what is actually wired

```bash
make claude-env      # structural validation + RUNTIME readiness (exit 5 = not wired)
```

`STRUCTURAL_PASS` means the files are correct. It says nothing about whether any
of them were loaded into this session; `RUNTIME:` is the line that answers that.
