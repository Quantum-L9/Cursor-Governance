# AGENTS.md — L9 Governance (Cursor-Governance)

Operating rules for any agent working **in** this repository, and the activation
contract for any agent working **in a repo that consumes** this repository.

Read this file before touching activation, hooks, or symlink wiring.

---

## 1. Mission of this repo

`Cursor-Governance` is the single source of truth for L9/Quantum-L9 agent
governance: rules, skills, slash commands, learning corpus, and the automation
that wires all of it into every coding workspace.

This repo owns:

- the governance content itself (`rules/`, `skills/`, `commands/`, `learning/`)
- the symlink/wiring contract (`CANONICAL_LAW.md`)
- the session activation hooks (`ops/hooks/`)
- the Graphiti memory client and activation runbooks (`ops/graphiti/`)

This repo does **not** own:

- repo-specific rules (those live in the consumer repo's `.cursor/rules/`)
- app/product code of any kind

---

## 2. Activation — how a session boots L9 governance

**There is exactly one activation mechanism, and it is automatic.**

### 2.1 Automatic (every session, no action needed)

`ops/hooks/session_start_bootstrap.sh` is installed as a real file at
`~/.cursor/hooks/session-start-bootstrap.sh` and registered in
`~/.cursor/hooks.json` under `sessionStart` (30s timeout). It runs on every
Cursor session start with no manual step:

1. Backgrounds `governance_sync.sh` — **bidirectional** reconcile of this clone
   against `origin/main`: fast-forward-only pull (never destroys local edits,
   never hard-resets), then a push via `backup_to_github.sh` so local work is
   backed up at session start too, not only on a clean session end. Set
   `GOVERNANCE_SYNC_PUSH=0` to make it pull-only.
2. Backgrounds `setup_claude_code_plugins.sh --quiet --workspace "$REPO"` —
   reconciles the declared Claude Code plugin set: a core set every governed
   workspace inherits (user-scope, `~/.claude/`), plus class-gated addons
   (project-scope, `<repo>/.claude/settings.json`) per `environment/plugins/`
   classification — see `environment/plugins/README.md`
3. Auto-wires `.cursor-commands` + `~/.cursor/{skills,commands,rules}`
   symlinks in the active workspace if any are missing
4. Backgrounds `install_ide_profile.sh --quiet` — reconciles the IDE profile
   declared in `environment/ide/` (extensions machine-wide, managed-key merge
   into the workspace's `.vscode/settings.json`)
5. Loads Graphiti env, scaffolds `memory-bank/` in the active workspace
6. Ensures the Graphiti SSH tunnel, then runs a health check
7. Reads a `memory-bank/activeContext.md` excerpt (T0 resume context)
8. Runs `check_governance_wiring.sh` and reports PASS/FAIL
9. Delegates to `ops/hooks/session_start_memory_orchestrator.sh` for
   code-graph health (PlasticOS repos) + Graphiti `inject "session start"`
   prefetch
10. Emits one combined `additional_context` JSON blob back to Cursor

### 2.2 Manual / on-demand commands

To re-run the **entire** sequence above against the current repo — same script,
synchronously, with output on your terminal instead of in a JSON payload:

```bash
make -C "$HOME/.cursor-governance" start WS="$(pwd)"
```

Consumer repos may add a two-line delegating `start` target so plain `make start`
works from inside the repo.

Same inheritance pattern for the local PR / security gate (no per-repo scanner
install beyond machine-level `gitleaks` + `uv`; bandit/semgrep/pip-audit run via
`uvx` from this clone). **Invariant:** `make pr` / PR pre-commit scan
**changed files only** (vs `PR_BASE`, default `origin/main`); full-corpus scans
are nightly CI (`make pr-full` / `make precommit` for intentional local full runs).

```bash
make -C "$HOME/.cursor-governance" pr WS="$(pwd)"
# or security scanners only:
make -C "$HOME/.cursor-governance" pr-security WS="$(pwd)"
```

When adopting **l9-ci-core**'s common workflow, consumer repos use the **identical
thin Makefile** from `tools/l9_repo/Makefile.template` (delegates to
`python -m tools.l9_repo`); they do **not** copy Cursor-Governance's fat Makefile.
Optional thin consumer Makefile that only delegates governance `pr`:

```makefile
pr:
	$(MAKE) -C "$(HOME)/.cursor-governance" pr WS="$(CURDIR)"
```

Run these directly if you need to re-check or repair only one piece mid-session:

```bash
bash "$HOME/.cursor-governance/ops/scripts/governance_sync.sh"
bash "$HOME/.cursor-governance/ops/scripts/check_governance_wiring.sh" "$(pwd)"
bash "$HOME/.cursor-governance/ops/scripts/setup_workspace_symlinks.sh"      # run from inside the consumer workspace, not from ~/.cursor-governance itself
bash "$HOME/.cursor-governance/ops/scripts/validate_governance_symlinks.sh"
bash "$HOME/.cursor-governance/ops/scripts/setup_claude_code_plugins.sh"     # reconcile Claude Code plugins; run from inside the consumer workspace (or pass --workspace)
bash "$HOME/.cursor-governance/ops/scripts/install_ide_profile.sh" "$(pwd)"  # reconcile IDE profile (--dry-run to preview)
python3 "$HOME/.cursor-governance/ops/graphiti/graphiti_memory_client.py" health
```

**Caution:** `setup_workspace_symlinks.sh` and `validate_governance_symlinks.sh`
resolve the workspace as `$(pwd)` — always `cd` into the consumer repo first.
Running them from inside `~/.cursor-governance` self-wires the SSOT clone as
if it were a consumer (harmless, but pointless; `.cursor-commands` and
`.cursor/` are gitignored here for exactly this reason). `setup_claude_code_plugins.sh`
defaults to `$(pwd)` the same way but also accepts an explicit `--workspace <path>`
(used by `setup_workspace_symlinks.sh` and the sessionStart hook internally) —
pass it directly if you're not `cd`'d into the target repo.

### 2.3 Toolchain pins (local `make pr` / pre-commit)

**Authority:** when [l9-ci-sdk](https://github.com/Quantum-L9/l9-ci-sdk) and
[l9-ci-core](https://github.com/Quantum-L9/l9-ci-core) disagree on a version,
**l9-ci-sdk wins**. Core is used only for tools the SDK does not pin
(gitleaks / bandit / pip-audit — SDK intentionally omits those).

**SSOT file in this repo:** [`requirements.txt`](requirements.txt) (exact pins +
comments). Keep `pyproject.toml` `[project.optional-dependencies] dev` and
`.pre-commit-config.yaml` ruff `rev` in lockstep with that file.

| Tool | Version | Install | Source |
|---|---|---|---|
| ruff | `0.16.0` | `uv sync --extra dev` | sdk `requirements-ci.txt` |
| mypy | `2.3.0` | same | sdk |
| pytest | `9.1.1` | same | sdk |
| pytest-cov | `7.1.0` | same | sdk |
| types-PyYAML | `6.0.12.20260724` | same | sdk |
| bandit | `1.8.6` | same / `uvx` | core `security.yml` (sdk omits) |
| pip-audit | `2.9.0` | same / `uvx` | core `security.yml` (sdk omits) |
| gitleaks | `8.24.3` | `brew install gitleaks` | core `security.yml` (sdk omits) |
| semgrep | `>=1.100.0,<2.0.0` | brew / pip / `uvx` | sdk SemgrepVersionPolicy |
| pre-commit | latest stable | pipx / pip / brew | framework only |
| uv | `>=0.8.0` | https://docs.astral.sh/uv/ | `[tool.uv] required-version` |

```bash
# One-time / refresh local analysis toolchain
uv pip install -r "$HOME/.cursor-governance/requirements.txt"
# preferred in this clone (locked):
make -C "$HOME/.cursor-governance" venv   # uv sync --locked --extra dev
brew install gitleaks                     # pin 8.24.3 when possible
```

**Not required for `make pr`:** `SEMGREP_APP_TOKEN` / `semgrep login` (optional
unthrottle / private rules), `SONAR_TOKEN` (SonarCloud / SonarLint only).

**Invariant:** `make pr` scans **changed files only**. Full-corpus = nightly CI
(`make precommit` / `make pr-full` for intentional local full runs).

### 2.4 Graphiti — activated (2026-07-27)

Graphiti memory is **fully activated and round-trip verified**, not degraded.
C1's `graphiti-mcp` container was found running `zepai/graphiti:latest` (a REST
API server with no `/mcp` endpoint — every tool call 404'd); it is now pinned
to `zepai/knowledge-graph-mcp:1.0.2-graphiti-0.28.2-standalone` per
`ops/graphiti/docker-compose.yml` + `ops/graphiti/config-docker-neo4j.yaml`.
The OpenAI key backing it was rotated (the prior key was revoked) and the
current key lives in AWS Secrets Manager (`l9/OPENAI_API_KEY`) — see
`ops/graphiti/graphiti.env.example`. `ops/graphiti/graphiti_memory_client.py`
was patched to match the real server's MCP protocol: session handshake
(`initialize` → `Mcp-Session-Id`), SSE response parsing, and the server's
actual tool/param names (`add_memory`, `search_memory_facts`, `group_ids` as
a list) — the client previously assumed names (`add_episode`, `search_facts`,
`group_id`) that never matched this deployment's `tools/list`.

Expect the health check to report `"graphiti: healthy"` / a successful
`tools/list`, not a degraded state. If you see `"MCP tools degraded"` again,
that is a regression — check the deployed image on C1
(`docker inspect graphiti-mcp-cursor --format '{{.Config.Image}}'` should say
`zepai/knowledge-graph-mcp`, not `zepai/graphiti`) before assuming this note
is stale.

### 2.5 Retired: `start-session.yaml`

A 917-line declarative YAML protocol of the same name previously existed at
the repo root. It was **deleted (2026-07-19)** — it was never wired into any
hook (Cursor doesn't execute YAML), and it had drifted from the pre-Graphiti
learning pipeline archived in `ops/scripts/_archived/`. Do not recreate a
YAML "protocol" file; the `.sh` hook above is the canonical activation
mechanism. If you need a human-readable narrative of what activation does,
this section is that narrative — keep it in sync with the hook, not a
separate spec file.

---

## 3. Source-of-truth files

- `CANONICAL_LAW.md` — symlink law, memory layer, anti-patterns (authoritative)
- `README.md` — directory structure and key-file index
- `ops/hooks/session_start_bootstrap.sh` — activation entry point (§2.1)
- `ops/scripts/resolve_governance_paths.sh` — path resolution (GitHub clone only, no Dropbox fallback)
- `ORG_INVARIANTS.yaml` — canonical Quantum-L9 org policy

Agents must keep code and these docs aligned — see `TODO.md` for known drift
not yet reconciled.

---

## 4. Symlink law (summary — `CANONICAL_LAW.md` §1-3 is authoritative)

| Workspace path | Target |
|---|---|
| `.cursor-commands` | `~/.cursor-governance/` (sole entry, every consumer repo) |
| `.cursor/governance/CANONICAL_LAW.md` | file symlink to the law file only |
| `.cursor/governance/` | local directory, **never** a symlink to the governance root |
| `~/.cursor/skills`, `~/.cursor/commands` | `~/.cursor-governance/skills/`, `~/.cursor-governance/commands/` |

Forbidden: a second governance tree in any repo, `.cursor/commands` or
`.cursor/skills` duplicating `.cursor-commands/*`, hard-reset/force-push of
this clone.

---

## 5. Change policy

### 5.1 Allowed
Bug fixes, dangling-reference repair, test/doc additions, new skills via
`l9-skill-compiler` → `l9-wire-skill-into-repo`.

### 5.2 High-risk — extreme care
Changes to `CANONICAL_LAW.md`, `resolve_governance_paths.sh`,
`backup_to_github.sh`, `ops/hooks/session_start_bootstrap.sh`, or anything in
`ops/scripts/_archived/` (archived = intentionally retired, not missing —
verify the archival rationale in git history before restoring anything).

### 5.3 Forbidden
- Reintroducing Dropbox as an SSOT fallback in any resolver script
- Restoring archived pre-Graphiti daemons without confirming they're not
  superseded (check `git log` for the archiving commit's stated rationale
  first)
- A new YAML/manual "protocol" file duplicating the `.sh` hook's job

---

## 6. Validation workflow before merge

```bash
bash ops/scripts/check_governance_wiring.sh "$(pwd)"
bash ops/scripts/validate_governance_symlinks.sh
bash ops/scripts/validate_governance_no_hardcoded_paths.sh
python3 ops/graphiti/graphiti_memory_client.py health   # expect healthy — see §2.3
```

---

## 7. Guidance for AI coding agents

- Before restoring anything from `ops/scripts/_archived/`, run
  `git log --oneline -- ops/scripts/_archived/<file>` and read the archiving
  commit's PR description. "Nothing references it" is not sufficient
  justification to restore it, and archival is not sufficient justification
  to assume it's safe to delete permanently either — check intent both ways.
- Prefer fixing the stale artifact over restoring the retired one. When a
  verification script fails because it checks a pre-archive path, the script
  is usually the thing that's stale, not the archive.
- This repo reconciles with `origin/main` in **both directions at session start**
  (`governance_sync.sh`: ff-only pull, then push via `backup_to_github.sh`) and
  pushes again at session end (`backup_to_github.sh` via the `sessionEnd` hook).
  Both directions are commit-preserving: the pull is fast-forward-only, the push
  rebases and aborts rather than committing over a conflict. Never hand-edit
  files in a way that assumes a different sync model.
- The session-end push is gated by `ops/scripts/backup_gate.sh`, because
  `sessionEnd` fires once per composer conversation (aborted chats and window
  closes included) and would otherwise commit a tree an agent is still writing.
  If a backup you expected did not happen, read `backup.log` — every skip is
  logged with its reason. Do not weaken the gate to force a backup through; run
  `make backup` (ungated) or set `GOVERNANCE_BACKUP_FORCE=1`.

---

## 8. Final principle

This repo is the governance boundary for every L9/Quantum-L9 coding workspace.
Activation must stay boring and automatic — one hook, one clone, one symlink
per consumer repo. Optimize for that staying true; do not add a second
activation path, however convenient it seems in the moment.

<!-- BEGIN L9 FORMATTER OWNERSHIP (generated — do not edit) -->

## Formatter ownership

Workspace class: `biome_default` — Default for every governed workspace: Biome owns JS/TS/JSON, Ruff owns Python.

Exactly one formatter owns each language. Do not reformat a file with a tool other than its owner, and do not add config for a competing formatter: the result is a diff that churns on every save.

| Languages | Owner | Note |
|---|---|---|
| `javascript`, `javascriptreact`, `typescript`, `typescriptreact`, `json`, `jsonc` | **biome** | bound by the governed IDE profile |
| `python` | **ruff** | bound by the governed IDE profile |

Generated from `environment/ide/policy.json` in the governance clone by `ops/scripts/adapters/agentdocs.sh`. Edit the policy, not this block.

<!-- END L9 FORMATTER OWNERSHIP -->
