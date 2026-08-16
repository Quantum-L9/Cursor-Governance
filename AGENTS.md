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

## 2.0 Bounded autonomy (Cursor SOP)

For parallel non-dependent Tasks and **background PR-poll while the main agent
continues**, use `/autonomy` and skill `l9-bounded-autonomy` (explicit-only).
Authority is a **campaign authorization packet** (not an envelope). Claude Code
machine runtime remains `environment/claude-code/autonomy/` — see its README
“Cursor SOP” link. Human merge only; do not rewrite the Python scheduler from Cursor.

### 2.0.1 Adapter Autonomy Velocity (Claude Code / peers)

SSOT: `ops/autonomy/surface_profile.yaml` (CANONICAL_LAW §6.1). On adapter
surfaces with `L9_AUTONOMY_ENABLED=true`, scoped commit/push/PR/remediation is
authorized without per-action ask; merge is denied by `ops/autonomy/merge_gate.py`.
Install settings: `make claude-settings WS="$(pwd)"`. Cursor remains ask-first
except campaign packet / `make pr` remediation.

### 2.0.2 L4 Local Autonomy (no mid-execution push)

SSOT: `ops/autonomy/surface_profile.yaml` → `l4_local_autonomy`
(CANONICAL_LAW §6.2). Default ON (`L9_L4_LOCAL_AUTONOMY=1`).

Proceed L4: stacked-branch **local commits only** through program/contract
execution — **no mid-execution push**, no push-approval pacing stalls. When
finished locally, run `kernels/Recursive Alignment.md` then
`kernels/Validate & Repair.md` on everything, then:

```bash
python3 ops/autonomy/l4_local.py begin --contract-id "<id>"   # if not begun
python3 ops/autonomy/l4_local.py record-kernels
python3 ops/autonomy/l4_local.py authorize-release
make pr   # push + open scoped PR using PULL_REQUEST_TEMPLATE.md
# then: l9-pr-remediation Converge → green → resolve review threads
# then: if user authorized merge — merge; older open PRs first (bottom-up)
```

After push: run `l9-pr-remediation` until green, resolve all code-review agent
comments, reach mergeable. When the user authorizes merge, merge. If older open
PRs exist (earlier `createdAt`), remediate and merge those **bottom-up first**
so older work lands before newer tips (avoids rebasing old PRs onto new main).

Enforcement: `ops/autonomy/local_execution_gate.py` (Claude PreToolUse + Cursor
`beforeShellExecution`) and `open_pr_after_gate.sh`. Status:
`python3 ops/autonomy/l4_local.py status`.

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

### 2.6 AWS secrets registry + UI operator (2026-08-06)

**SSOT:** this repository owns `ops/secrets/openclaw-igorbot.registry.yaml`.
Sync pulls secret names (and JSON key names) from AWS Secrets Manager under
namespace `openclaw-igorbot/*` (region `us-east-1`). Consumers (igorbot, bots,
CI) depend on this registry — do not reverse the dependency.

| Piece | Path / command |
|---|---|
| Registry + resolve | `ops/secrets/` — `make secrets-sync`, `make secrets-check REF='…'` |
| Skill (refs) | `l9-aws-secrets` |
| UI console + cartridges | `ops/ui-operator/` — skill `l9-ui-operator` (explicit-only) |
| Optional install | `make ui-operator-sync` → `uv sync --extra ui-operator && playwright install` |

**Rules:** secret **values** never in git/logs/receipts; inventory is IDs/keys
only; no macOS Keychain or daily-Chrome cookie decrypt for governed UI
automation; diagnose before mutating vault contents; UI receipts redact values.

**GitHub authority (CANONICAL_LAW.md §14):** agents **MUST** resolve
`openclaw-igorbot/github#token` for `gh`/API work and **MUST NOT** ask the
human to operate `github.com` UI when that PAT can complete the outcome. Do
**not** provision a second GitHub PAT in AWS while this ref works.

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

**Cursor-primary ownership (`CANONICAL_LAW.md` §2.1):** build shared capability
in Cursor-primary / `ops/` first; wrap outward for Claude Code and other
adapters. Never implement a shared brain under `environment/claude-code/` and
have Cursor import it — that is adapter spaghetti.

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

`pyproject.toml` is a **protected file** (`ORG_INVARIANTS.yaml` `protected_paths`
+ CODEOWNERS): it pins the dependency/interpreter contract and the local
`make pr` / pre-commit gate config. **Append only — never overwrite existing
keys or lines.** Single-key TOML fields such as `[tool.pytest.ini_options]`
`addopts` cannot be extended by appending; put additive pytest collection
controls in the root `conftest.py` instead of rewriting the field here.

### 5.3 Forbidden
- Reintroducing Dropbox as an SSOT fallback in any resolver script
- Owning shared cross-surface capability under a dependent adapter and wrapping
  Cursor to consume it (violates `CANONICAL_LAW.md` §2.1)
- Restoring archived pre-Graphiti daemons without confirming they're not
  superseded (check `git log` for the archiving commit's stated rationale
  first)
- A new YAML/manual "protocol" file duplicating the `.sh` hook's job

---

## 6. Validation workflow before merge

**Binding pre-PR gate (`CANONICAL_LAW.md` §12) — non-optional, fail-closed.**
Before opening *any* PR (opening or updating a PR triggers CI), the local
changed-files pipeline MUST pass:

```bash
make pr-check  # gate only — changed-files pre-commit + ruff + security
make pr        # gate → open PR → subscribe → agent spawns l9-pr-remediation
```

Do not open the PR, and do not push to trigger CI, if `make pr` / `make pr-check`
fails — fix and re-run first. `make pr` / `make PR` / `make Pr` / `make pR` are
equivalent (Makefile remaps any capitalization of `pr`).

`make pr` auto-heals derived artifacts via `ops/scripts/sync_generated_artifacts.py`
(RULES-MANIFEST, skill-registry, skillOverrides, COMMANDS_MANIFEST, PE digests,
orphan skills → `explicit_only`). Regenerated files are a **WARN to stage**, not
a hard fail. On a local governance clone it also reconciles Claude skills and
fail-closes on hooks/bootstrap/plugin wiring.

After the gate PASSes, `make pr` (any capitalization) runs
`ops/scripts/open_pr_after_gate.sh`: push the feature branch, open or reuse the
GitHub PR, subscribe to PR notifications, write
`memory-bank/pr-remediation-handoff.json`, and print an `L9_AGENT_REQUIRED`
block. **Any agent that sees that block MUST immediately** spawn a background
Task (`run_in_background=true`) using `l9-pr-remediation` + the
`poll_worker` template in `skills/l9-bounded-autonomy/references/prompt-templates.md`
(packet fields from the handoff JSON). Cap 3 fix-push cycles; never merge;
never force-push; main agent continues (do not AwaitShell on that PR). Use
`make pr-check`, `OPEN_PR=0 make pr`, or `PR_REMEDIATE=0 make pr` to skip
open and/or remediation spawn. Opening requires commits ahead of `PR_BASE`
(default `origin/main`) and refuses `main`/`master`.

Then run the governance-wiring checks:

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

Workspace class: `biome_default` — Default for every governed workspace: Biome owns JS/TS/JSON, VS Code JSON language features owns JSONC (the Biome extension cannot format jsonc), Ruff owns Python.

Exactly one formatter owns each language. Do not reformat a file with a tool other than its owner, and do not add config for a competing formatter: the result is a diff that churns on every save.

| Languages | Owner | Note |
|---|---|---|
| `javascript`, `javascriptreact`, `typescript`, `typescriptreact`, `json` | **biome** | bound by the governed IDE profile |
| `jsonc` | **vscode-json** | bound by the governed IDE profile |
| `python` | **ruff** | bound by the governed IDE profile |

Generated from `environment/ide/policy.json` in the governance clone by `ops/scripts/adapters/agentdocs.sh`. Edit the policy, not this block.

<!-- END L9 FORMATTER OWNERSHIP -->
<!-- PROGRAM_EXECUTION_ADAPTER_LAYER_V1:AGENTS -->

## Program Execution adapter layer

The reusable subsystem lives at `environment/program-execution/`. Do not copy its
core schemas, root `autonomy/`, the Claude bounded-autonomy scheduler, the agent
registry, or the Graphiti client into an adapter.

Program Execution tasks use the Program Execution Controller lease as the sole
authoritative work claim. They must not acquire a competing Graphiti task claim.
A Graphiti projection is observability only and is never authoritative.

Validation:

```bash
make program-execution-core-validate
make program-execution-adapters
make program-execution-conformance
make program-execution-probe
make pr
```

<!-- ROOT_FILE_APPEND_ONLY_PROTECTION_V1 -->

## Repository-root files are append-only

Every file at the repository root is protected. Incoming changes may **add**
content freely, but may **not delete or overwrite** existing content in a
protected root file without both:

1. an `ALLOW-ROOT-DELETION: <path> — <reason with proof of necessity>` line in a
   commit message (highlighting the delta and justifying the removal), and
2. CODEOWNERS approval from the repository owner.

The authoritative protected-file list and the per-file rule live in
`ops/config/root-file-protection.json`. Three tiers apply (every tier is
CODEOWNERS-reviewed; the tier only decides whether the additive gate also fires):

- **additive_only** (governance, legal, dependency, gate/security, and
  environment-modifying files): deletions/overwrites fail the gate without a
  justification marker.
- **managed** (living/operational/community docs and low-risk config — e.g.
  `README.md`, `CHANGELOG.md`, `TODO.md`, `.env.example`): edited freely with owner
  review; no marker required, not additive-locked.
- **regenerable** (machine-generated artifacts — `uv.lock`,
  `governance-health-report.json`, `.harvest_executor_state.json`): exempt from the
  additive check because they are rewritten wholesale by tooling.

A new repository-root file must be registered in the policy with a tier — an
unregistered new root file fails the gate, so "every root file is protected"
cannot be silently bypassed by adding one.

Enforcement is mechanical and fail-closed on every pull request via
`.github/workflows/root-file-protection.yml` →
`ops/scripts/validate_root_file_protection.py`. The gate is read-only and never
edits files. Removing or weakening the gate is itself a protected-path change
(`ORG_INVARIANTS.yaml` `protected_paths`). Every change stays traceable to its
originating commit/agent and is reversible with `git revert`.

<!-- MEMORY_BANK_RETIRED_APPEND_V1 -->
## memory-bank/ retired (2026-08-11) — supersedes §2.1 steps 5/7 and §6 handoff path

Authoritative corrections (do not treat older bullets above as SSOT):

1. SessionStart does **not** scaffold `memory-bank/` and does **not** excerpt
   `memory-bank/activeContext.md`. Resume SSOT is Graphiti (`inject` / PICKUP /
   hydration). See `ops/graphiti/MEMORY_BANK_POLICY.md` and
   `docs/MEMORY_PIPELINE_MAP.md`.
2. After `make pr` opens a PR, the remediation handoff path is
   `.l9/pr/pr-remediation-handoff.json` (written by
   `ops/scripts/open_pr_after_gate.sh`), **not**
   `memory-bank/pr-remediation-handoff.json`. Rule `98-make-pr-remediation`
   matches this path.
3. Residual `memory-bank/` trees are archival residue; wiring checks WARN if
   present and PASS when absent. Agents must not recreate them.

<!-- L4_PROGRAM_BUILD_IMPLIES_MERGE_V1 -->
## L4 program/plan Build implies merge (2026-08-12) — supersedes §2.0.2 merge phrasing

Authoritative correction (do not treat older “when the user authorizes merge”
bullets above as requiring a second ask):

1. Launching a program or clicking Build on a plan **is** merge authorization
   for that stack. After `l9-pr-remediation` reaches green + mergeable: merge.
2. Older open PRs (earlier `createdAt`): remediate and merge **bottom-up first**.
3. Merge outside that L4 program/plan Build stack still requires
   `L9_MERGE_AUTHORIZED` (or a valid L4 release receipt for ordinary
   `gh pr merge` via `ops/autonomy/merge_gate.py`). Force-push / admin-merge /
   hard-reset remain forbidden.

<!-- CLAUDE_CODE_ADAPTER_PLACEMENT_V1 -->
## Claude Code adapter placement (2026-08-12)

Claude Code gold-standard pack lives at
`environment/agents/adapters/claude-code/`. A transitional symlink may exist at
`environment/claude-code` until extinguishment. Cloud Web/Mobile memory uses
HTTPS Graphiti (`GRAPHITI_MCP_URL=https://memory.quantumaipartners.com/graphiti/mcp`);
see ADR-0006 + ADR-0007.

<!-- CLAUDE_CODE_SYMLINK_EXTINGUISHED_V1 -->
## Claude Code symlink extinguished (2026-08-12) — supersedes §2.0 autonomy path + placement symlink note

Authoritative corrections:

1. Sole pack home is `environment/agents/adapters/claude-code/` (including
   `autonomy/`). Do not teach `environment/claude-code/` as a live path.
2. The transitional symlink `environment/claude-code` is **removed**.
3. Older bullets naming `environment/claude-code/autonomy/` as the machine
   runtime are historical; use the adapters path.


<!-- GOVERNANCE_ACTIVATE_FRESH_SESSIONSTART_V1 -->
## SessionStart tip activation (2026-08-12) — supersedes §2.1 step 1 and related bullets

Authoritative corrections (do not treat older §2.1 / §2.2 bullets above as SSOT
where they conflict):

1. `sessionStart` timeout is **60s** (not 30s).
2. Step 1 is foreground `governance_activate_fresh.sh` **before** resolving the
   SSOT — tip authority is GitHub `origin/main` (ff-only when safe, else shallow
   clone + atomic swap). Prefers
   `$HOME/.cursor-governance/ops/scripts/governance_activate_fresh.sh`, then the
   `~/.cursor/hooks/governance-activate-fresh.sh` sidecar; chicken-egg minimal
   clone if both are missing. Parses the STATUS line
   (`action` / `sha` / `remote_sha` / `detail`).
   `governance_sync.sh` remains available for manual / on-demand bidirectional
   reconcile; it is **not** the sessionStart tip-activation step.
3. Auto-wire targets: consumer `.cursor-commands`, `.cursor/plans` →
   `~/.cursor/plans`, and the `l9-governance` plugin when missing. SSOT must
   **not** self-alias `.cursor-commands`.
4. `check_governance_wiring.sh` reports PASS/FAIL including tip freshness
   (`HEAD == origin/main`).
5. Memory orchestrator emits Graphiti hydrate packet stats
   (`hydrate_stats`: facts_returned, pickup_parsed, …) with
   `inject "session start"`.
6. Combined `additional_context` is sectioned markdown (Governance / Runtime /
   Graphiti hydrate / Code-graph) via COMBINED env to Python; exit 0 always.
7. On-demand repair set includes:
   `bash "$HOME/.cursor-governance/ops/scripts/governance_activate_fresh.sh"`.
8. Running symlink setup from inside `~/.cursor-governance` must **not** create
   a `.cursor-commands` self-alias (setup removes it). Prefer wiring consumers,
   not the SSOT clone.

<!-- INFISICAL_CURSOR_GOVERNANCE_VAULT_V1 -->
## Infisical Cursor-Governance vault (2026-08-13) — extends §2.6

Authoritative additions (do not treat older §2.6 bullets as Infisical-unaware):

1. Long-term secret **values** for this agent live in Infisical project
   **Cursor-Governance** (`slug: cursor-governance`, env `prod`, path `/`
   as env-var names). Inventory of IDs/key names:
   `ops/secrets/infisical-cursor-governance.yaml`.
2. AWS `openclaw-igorbot/*` remains the name-inventory SSOT and the chicken-egg
   Universal Auth bootstrap. Hydrate Infisical from
   `openclaw-igorbot/infisical-cursor-governance`
   (`INFISICAL_CLIENT_ID` / `_SECRET` / `INFISICAL_PROJECT_ID` / `INFISICAL_ENV=prod`).
3. Skill `l9-aws-secrets` covers **both** vaults. Agents MUST resolve via that
   skill before asking the human. Values never in git/logs/chat.
4. Re-port AWS → Infisical: `python3 ops/secrets/port_aws_to_infisical.py`.

<!-- CHAT_TRANSCRIPT_S3_ARCHIVE_V1 -->
## Closed-chat word archive (2026-08-13)

Authoritative additions:

1. Hourly `ops/scripts/export_chats.sh` and tenx `com.tenx.learning-processor`
   (`memory_aggregator.py`) are retired. They never captured nested `.jsonl` words.
2. On chat X-out (`sessionEnd`), archive user/assistant text + timestamps to S3
   `l9-chat-transcripts-020125249784` (`python -m ops.graphiti.hydration.archive_transcript`).
   Not GitHub, not a local-only copy. No sqlite.
3. See `ops/scripts/RETIRED_export_chats_and_learning_processor.md`.

<!-- KERNEL_PACK_NEW_BRANCH_DEFAULT_V1 -->
## KERNEL pack landing branch default (2026-08-13)

Do **not** ask whether to land a KERNEL pack, PE overlay, or similar governed
architecture change on the current feature branch vs a new branch.

Default, without asking:

1. Create a **new branch from `origin/main`** (ff-only tip) in this clone.
2. Do **not** mix unrelated WIP (legal ingest, other feature work) into that
   branch.
3. Ask only if the user already named the target branch as the subject of the
   change, or `origin/main` cannot be resolved.

Stock pack apply scripts that hard-reset or require a foreign `BASE_SHA` are
not the landing path in a dirty or unrelated checkout. Rule:
`rules/46-kernel-pack-new-branch.mdc`.

<!-- PEER_EXECUTION_CORE_RUNTIME_V1 -->
## Peer Execution shared runtime (2026-08-14)

Bounded concurrency runtime is provider-neutral at `environment/program-execution/peer_execution/autonomy/`. Every provider binds to the same shared runtime through Program Execution; no provider owns a scheduler. Human merge only.

<!-- RULES_CORPUS_CLEANUP_REFS_V1 -->
## Rules corpus cleanup refs (2026-08-14) — supersedes MEMORY_BANK_RETIRED rule id

Authoritative correction (do not treat the older `98-make-pr-remediation`
stem above as live):

1. Rule stem `98-make-pr-remediation` was renamed to `48-make-pr-remediation`
   (`rules/48-make-pr-remediation.mdc`) in rules-corpus-cleanup-v1.
2. Handoff path remains `.l9/pr/pr-remediation-handoff.json`.

<!-- PRECOMMIT_HOOK_ATTRIBUTION_V1 -->
## pre-commit "files were modified by this hook" names a window (2026-08-14)

`_run_single_hook` diffs the tracked worktree before and after each hook and
threads the result forward (`pre_commit/commands/run.py`). The message therefore
means "the tree changed while this hook was running" — **not** "this hook
wrote". `symlinks-check` has the widest window in this repo's hook set and
absorbs blame for concurrent writers; it is repo-read-only.

1. Do **not** audit the named hook first. Measure:

```bash
bash ops/scripts/attribute_tree_writers.sh "$(pwd)" <status-before> <precommit-log>
cat .l9/pr/gate-dirtiness.json
```

2. `make pr` no longer dies on that exit code. It separates a real
 `- exit code:` (FAIL, hook named) from a modified tree (classify → attribute →
 quiesce → retry once → FAIL with exact paths). `L9_GATE_STRICT_LEGACY=1`
 restores the old behavior.
3. Every hook is declared `read_only` or `writer` in
 `ops/config/precommit-hook-contract.json`; `make precommit-hook-contract`
 fails closed on drift.
4. Automated writers serialize behind `ops/scripts/lib/repo_write_lock.sh`
 (`make pr` holds it; sessionStart reconcilers yield). Machine-local and
 short-lived — distinct from the tracked `.governance-build-lock` kill switch,
 and not a substitute for a per-agent worktree (`rules/49`).
5. The gate's two dirtiness domains are reported apart: tracked (`git diff`,
 what pre-commit compares) and untracked (`git status --porcelain`).
 Untracked-only churn can never have produced the message.

Background: `learning/failures/precommit-hook-attribution.md`.

<!-- PLAN_AUDIT_SESSIONSTART_V1 -->
## SessionStart Plan audit (2026-08-12) — extends tip-activation §6 sections

Authoritative addition (do not treat older “Governance / Runtime / Graphiti
hydrate / Code-graph” lists as exhaustive):

1. Bootstrap `additional_context` also includes `### Plan audit`, produced by
   `skills/l9-plan-audit/scripts/audit_plans.py` (fail-open, ~2s budget).
2. Scans machine-global Cursor plans (`<workspace>/.cursor/plans` →
   `~/.cursor/plans`) for **unbuilt** plans with mtime in the last **7 days**
   and attaches staleness flags (see skill `references/staleness-rules.md`).
3. Findings are **display-only** — do not auto-Build. On-demand:
   `/plan-audit` → same CLI. `/start-session` STATE_SYNC surfaces the section.

<!-- CAMPAIGN_EXECUTION_MAKE_PR_NO_MERGE_V1 -->
## Campaign execution publish path (2026-08-14) — supersedes §2.0.2 / L4 merge phrasing

Authoritative corrections for Program Execution campaigns and default `make pr`:

1. After L4 kernels + `authorize-release`, agents MUST publish with
   `PR_REMEDIATE=0 make pr` so Makefile checkers run and only clean code is
   pushed. Do not use raw `gh pr create` as the publish path.
2. Do **not** remediate (`l9-pr-remediation` / poll workers). Do **not** merge.
   `ops/autonomy/merge_gate.py` no longer treats an L4 release receipt as merge
   authority. Human only: `L9_MERGE_AUTHORIZED`.
3. Each campaign has one integration branch. Land all campaign PRs into that
   branch (`PR_BASE=origin/campaign/<campaign_id>`). Do **not** open campaign
   PRs against `main`. Do **not** mix campaign work onto other feature branches.
4. Branch map and order: `environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml`.
   Profile SSOT: `ops/autonomy/surface_profile.yaml` → `campaign_execution`.

<!-- PR_REMEDIATION_AUTHORIZES_MERGE_V1 -->
## /l9-pr-remediation authorizes merge (2026-08-16) — supersedes campaign no-merge for remediations

Authoritative corrections (do not treat older “do not merge / Human only
`L9_MERGE_AUTHORIZED`” bullets as blocking this skill):

1. Campaigns and `make pr` still end at **green + merge-ready**. They do
   not merge. An L4 release receipt still does not authorize merge.
2. Invoking **`/l9-pr-remediation`** (Converge) **is** merge authorization
   for **all open PRs** in the target repo. Write
   `python3 ops/autonomy/authorize_merge.py --repo <owner/name> --all-open`,
   converge each PR, then `gh pr merge --squash --repo` oldest first.
3. `ops/autonomy/merge_gate.py` allows that ordinary merge after the
   receipt (or `L9_MERGE_AUTHORIZED`). Force-push, hard-reset, and
   `--admin` stay denied.
4. `/pr` remains Diagnose-only (no merge).

<!-- WIP_CORPUS_ON_MAIN_V1 -->
## WIP corpus on main (2026-08-16) — supersedes “agents never touch WIP”

Authoritative corrections (do not treat older “never read or write WIP” or
`current_work/` bullets as SSOT):

1. `WIP/` is a **dated tracked corpus on `main`**. Prefer
   `WIP/<M-D-YY>/<topic>/`. Named series (`WIP/CG/`) stay and are inventoried.
2. Agents **may** read/write WIP for hygiene, filing loose root notes, and
   high-evidence prune (`make wip-hygiene` / `ops/scripts/wip_corpus.py`).
3. Auto-prune only when a WIP file’s sha256 matches a tracked **non-WIP**
   path, or inventory has an explicit `landed:` marker. Unique WIP is kept.
   Receipts live in `WIP/_receipts/`. Git history is the undo.
4. Do **not** park WIP under `/tmp` or `.l9/scratch-hold/`. Stage with
   pathspecs only (rule 49). `WIP/Legal Defense/` and credential globs stay
   untracked. Scanner excludes of `WIP/**` stay in place.
5. `TODO.md` remains the agent task queue. `l9-git-work-preserve` still
   inventories git refs/stashes and never auto-deletes branches.
