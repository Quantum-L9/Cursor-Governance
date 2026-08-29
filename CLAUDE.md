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

This file is not a rung. It only names them.

Maps, not rungs — live at **this repo's root**, not org-seeded, not competing
SSOTs:

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — this-repo module / CI index
- [`INVARIANTS.md`](INVARIANTS.md) — this-repo invariant + CI enforcement index
- [`ORG_INVARIANTS.yaml`](ORG_INVARIANTS.yaml) — machine org-policy SSOT
  (`INVARIANTS.md` points at it; do not copy `L9-ORG-*` bodies here)

Resume SSOT is Graphiti (`inject` / PICKUP). Do not write `memory-bank/`.
Activation is SessionStart only (`AGENTS.md` §2). Publish is
`PR_REMEDIATE=0 make pr` (`make PR` / `Pr` / `pR` are the same target).
Consumers do not inherit this file from the Quantum-L9/.github seeder; they
keep their own `CLAUDE.md` if they have one (`agentdocs.sh` only maintains
the formatter block).

## The things most often got wrong here

- **`make pr` (any capitalization) is the sanctioned route to GitHub — and
  nothing blocks the alternatives.** Raw `git push` is *not* denied by
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
- **Local `git commit` runs no hooks here, and that is deliberate.** This repo
  installs no commit hook — `pre-commit install` is *forbidden*
  (`validate_claude_env.check_session_deps_installs_no_git_hook`,
  `ops/scripts/run_pr_precommit.sh`), because a raw hook runs the catalog
  without the surface-aware SKIP list. Verification lives at `make pr`
  (Diagnose: `OPEN_PR=0 make pr`). So never reach for `--no-verify`,
  `git commit -n`, `-c core.hooksPath=`, or `SKIP=`/`HUSKY=`: there is no hook
  to skip, the token only signals intent to dodge verification, and
  `ops/autonomy/verification_bypass_gate.py` denies it at PreToolUse. If you
  want the checks, run `OPEN_PR=0 make pr`.
- **Receipts expire.** `~/.l9/claude/bootstrap-state.json` and
  `~/.l9/claude/gov-refresh.json` carry a UTC timestamp and a TTL. Read them
  through `ops/scripts/claude_bootstrap_receipt.py` and
  `ops/scripts/governance_refresh_receipt.py`, which recompute state rather than
  trusting the recorded word. An absent receipt means `never_ran`, not `ready`.

## Checking what is actually wired

```bash
make claude-env      # structural validation + RUNTIME readiness (exit 5 = not wired)
```

Every step of that target runs even when an earlier one fails, so the `RUNTIME:`
line is always printed. A structural failure still decides the exit code, so
exit 5 means specifically: the files are correct and nothing loaded them.

`STRUCTURAL_PASS` means the files are correct. It says nothing about whether any
of them were loaded into this session; `RUNTIME:` is the line that answers that.

This file is `managed` (rewrite allowed, no `ALLOW-ROOT-DELETION`). Twelve root
files are `additive_only` — among them `pyproject.toml`, `requirements.txt`,
`conftest.py`, and `.pre-commit-config.yaml`, not only the obvious `Makefile`
and `AGENTS.md`. Adding lines to one is free. **Removing or overwriting a line
needs `ALLOW-ROOT-DELETION: <path> — <reason>` in a commit message on the
branch** (any commit in the range counts) plus CODEOWNERS approval, and the PR
must use `.github/PULL_REQUEST_TEMPLATE/protected-root.md`
(`<!-- L9_PROTECTED_ROOT_PR -->`). `make pr` injects the template but cannot
invent the marker; without it the gate blocks the push. Authoritative list:
`ops/config/root-file-protection.json`. Full rule: `AGENTS.md` §14.
`ops/autonomy/root_file_advisory.py` warns at the start of a turn when a
protected root file is being overwritten without its marker, so this is caught
at edit time rather than at push.

<!-- BEGIN L9 FORMATTER OWNERSHIP (generated — do not edit) -->

## Formatter ownership

Workspace class: `biome_default` — Default for every governed workspace: Biome owns JS/TS/JSON, VS Code JSON language features owns JSONC (the Biome extension cannot format jsonc), Ruff owns Python, Prettier owns Markdown (format-on-save off so governance docs do not churn).

Exactly one formatter owns each language. Do not reformat a file with a tool other than its owner, and do not add config for a competing formatter: the result is a diff that churns on every save.

| Languages | Owner | Note |
|---|---|---|
| `javascript`, `javascriptreact`, `typescript`, `typescriptreact`, `json` | **biome** | bound by the governed IDE profile |
| `jsonc` | **vscode-json** | bound by the governed IDE profile |
| `python` | **ruff** | bound by the governed IDE profile |
| `markdown` | **prettier** | bound by the governed IDE profile |

Generated from `environment/ide/policy.json` in the governance clone by `ops/scripts/adapters/agentdocs.sh`. Edit the policy, not this block.

<!-- END L9 FORMATTER OWNERSHIP -->
