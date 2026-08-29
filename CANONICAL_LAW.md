<!-- L9_META
l9_schema: 1
origin: l9-deployment-platform
layer:
- repository
tags:
- L9_META
- deployment-platform
owner: platform
status: active
/L9_META -->
# L9 Governance — Canonical Law

**Status:** authoritative
**Runtime:** L9 Governance
**Governance root (SSOT):** `$HOME/.cursor-governance/` — the GitHub clone
**GitHub origin (SSOT remote):** `Quantum-L9/Cursor-Governance`
**Updated:** 2026-08-07 (integration-branch-first + local runtime discipline §13)

---

## 1. Single Source of Truth

| Asset | Canonical path | Access method |
|-------|----------------|---------------|
| **Governance body** | `~/.cursor-governance/` (clone root) | `.cursor-commands/` symlink |
| CANONICAL_LAW | `~/.cursor-governance/CANONICAL_LAW.md` | `.cursor/governance/CANONICAL_LAW.md` (file symlink) |
| L9 skills | `skills/` (live packs only; retired → `skills/_archived/`) | `@.cursor-commands/skills/` |
| Workflows/DAGs | `workflows/dags/` | Executed by DAG runner |
| Global rules | `rules/*.mdc` (SSOT) | Cursor: `@.cursor-commands/rules/` via `l9-governance` plugin |
| LLM rules (.md peers) | `environment/generated/llm-rules/` (projected; do not hand-edit) | Claude: `.claude/rules` → generated mount via `reconcile_llm_rule_adapters.py` |
| Ops scripts | `ops/scripts/` | `.cursor-commands/ops/scripts/` |
| Intelligence | `intelligence/` | Active signal corpus (never archive) |
| **Org invariants** | `~/.cursor-governance/ORG_INVARIANTS.yaml` | Canonical Quantum-L9 policy; mirrored to consumer repos |
| **Executable plan template** | `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` | First-class primitive (`MANIFEST.yaml`); `/plan` + `l9-plan` default projection; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only |
| **Autonomy family** | `environment/contracts/autonomy/MANIFEST.yaml` | First-class subordinate primitive family (root `autonomy/` + `ops/autonomy` + Claude scheduler SSOTs); PE Controller remains authoritative; `owns_program_state: false`; validate via `make autonomy-contracts-validate` |
| **Peer Execution thin-adapter law** | `environment/contracts/execution/PEER_EXECUTION_THIN_ADAPTER_LAW.yaml` | Binding provider-neutral execution architecture; validate via `make peer-execution-conformance` |

**Law:** The governance repo appears **once** in each workspace: `.cursor-commands` → clone root.
**Never** expose the governance root under `.cursor/governance/` — that path holds only the law file + README.

---

## 2. IDE Adapter Model

This governance layer is **IDE-agnostic at the consumption edge**. The
`.cursor-commands/` symlink is one adapter. Future adapters (Windsurf, VS Code,
CLI) will consume the same root via their own conventions.

| Adapter | Entry point | Status |
|---------|-------------|--------|
| Cursor | `.cursor-commands/` → clone root; `l9-governance` local plugin | Active (**primary coding surface**) |
| Claude Code (CLI · Web · Mobile) | `environment/agents/adapters/claude-code/` — committed `.claude/` + account environment | Active (**dependent adapter**) |
| Manus | `environment/agents/adapters/manus/` — connector + env + session bootstrap, identity from `environment/agents/agent_registry.yaml` | Active |
| Codex / OpenAI | `environment/agents/adapters/codex/` — AGENTS.md block + env, identity from `environment/agents/agent_registry.yaml` | Planned |
| Gemini CLI | `environment/agents/adapters/gemini/` — settings template + env, identity from `environment/agents/agent_registry.yaml` | Planned |
| Windsurf | TBD | Planned |
| VS Code | TBD | Planned |
| CLI (direct) | Direct path reference | Active |

### 2.1 Cursor-primary capability ownership (anti-spaghetti)

**This repo is `Cursor-Governance`.** Cursor is the superior coding surface for
authoritative product work. Other LLM/IDE runtimes (Claude Code, Codex, Gemini,
Manus, …) are **dependent adapters** that consume this SSOT. They are surface
peers for *activation shape* (hooks, settings templates, discovery paths) — they
are **not** owners of shared capability.

**Law — build inward, wrap outward:**

1. Implement shared capability **first** in Cursor-primary (or adapter-neutral)
   homes: `ops/`, `rules/`, `skills/`, `commands/`, top-level governance contracts.
2. Only then add a **thin adapter wrapper** under `environment/<adapter>/` (or
   `environment/agents/adapters/<adapter>/`) that binds the same capability to
   that surface’s hooks, settings, and discovery paths.
3. Adapters may narrow, translate, or fail-open for surface limits. Adapters must
   **never** become the implementation home that Cursor then imports.

**Forbidden (causes spaghetti):**

| Anti-pattern | Why |
|---|---|
| Shared scorer / router / autonomy brain lives under `environment/claude-code/` or `environment/agents/adapters/claude-code/` and Cursor imports it | Inverts ownership — Claude adapter owns Cursor’s brain |
| “Claude implemented it; wrap Cursor to reuse Claude” | Dependent adapter dictating the SSOT |
| Duplicating the same brain in each adapter folder | Drift and dual maintenance |
| Treating “peer of `environment/ide/`” as equal ownership of cross-surface logic | Peer = surface parity, not capability ownership |

**Required shape:**

| Layer | Owner | Example |
|---|---|---|
| Shared capability | Cursor-primary / adapter-neutral governance | `ops/hooks/*`, `ops/scripts/*`, `rules/*`, `skills/*`, shared libs under `ops/` |
| Cursor binding | Cursor adapter paths | `~/.cursor/hooks.json`, `l9-governance` plugin, `.cursor-commands` |
| Other LLM/IDE binding | Thin wrapper only | `environment/agents/adapters/claude-code/hooks/*` imports shared ops; does not own the scorer |

**Skill routing ownership:** shared scoring lives in `ops/skill_routing/`;
registry at `ops/generated/skill-registry.json`. Claude and Cursor hooks are
thin I/O adapters only.

Multi-agent identity (WHO writes memory: agent IDs, roles, tokens-by-name) is
governed by `environment/agents/agent_registry.yaml` — peer of
`ops/graphiti/group_registry.yaml` (WHAT repo memory is about). Validate with
`make agents-env`. See `environment/agents/README.md`.

The Claude Code adapter is defined in `environment/agents/adapters/claude-code/` (surface peer of
`environment/ide/` for activation templates — **not** capability owner). It
reuses `environment/ide/policy.json` unchanged; formatter ownership reaches a
Claude Code session through the `agentdocs` `CLAUDE.md` block, not a second
authority. It adds **no** second activation path for Cursor. On Claude Code
Web/Mobile the sandbox is cloned fresh and reclaimed per session, so its
activation is carried by **git-tracked** files (`.claude/settings.json`, the
SessionStart hook, `.mcp.json`) plus the account-level environment — never by
`~/.cursor/` machine state, which never reaches the sandbox.

### Required symlinks — every coding workspace

| Workspace path | Target | Purpose |
|----------------|--------|---------|
| `.cursor-commands` | `~/.cursor-governance/` | Sole global entry |
| `.cursor/governance/CANONICAL_LAW.md` | `~/.cursor-governance/CANONICAL_LAW.md` | Law file only |
| `.cursor/governance/` | **local directory** | Not a symlink to governance root |

### Forbidden

| Path | Why |
|------|-----|
| `.cursor/governance` → governance root | Exposes duplicate tree |
| `.cursor/governance/GlobalCommands` | Legacy duplicate |
| `.cursor/commands` | Duplicate of `.cursor-commands/commands` |
| `.cursor/skills` | Duplicate of `.cursor-commands/skills` |
| `.cursor/rules` → governance root/`rules/` (whole-dir or selective) | Retired by rule 84 v3.0.0 — served by the `l9-governance` Cursor plugin instead |

---

## 3. User-Level Configuration (every machine)

Governance loads as a Cursor **local plugin**, not as `~/.cursor/{rules,skills,
commands}` symlinks — see rule `84-cursor-governance-wiring.mdc` v3.0.0 and
`environment/plugins/README.md` for the full model, including per-class addon
plugins.

| Path | Target |
|------|--------|
| `~/.cursor/plugins/local/l9-governance` | `~/.cursor-governance/` (clone root; `.cursor-plugin/plugin.json` at root names the plugin) |

**Retired (do not recreate):** `~/.cursor/skills`, `~/.cursor/commands`,
`~/.cursor/rules` as whole-directory symlinks to governance. Cursor discovers
`rules/`, `skills/`, `commands/` under the plugin root itself.

---

## 4. Naming Conventions

| Prefix | Location |
|--------|----------|
| `l9-*` | `skills/` |
| `plasticos-*` | Repo-local `.claude/skills/` |
| Repo rules | Repo `.cursor/rules/` only |

---

## 5. GitHub SSOT

| Item | Value |
|------|-------|
| Remote (origin) | `https://github.com/Quantum-L9/Cursor-Governance.git` |
| Branch | `main` |
| Git root | `~/.cursor-governance` |
| Pull (session start) | `governance_sync.sh` — guarded ff-only |
| Push (session end) | `backup_to_github.sh` — commits + rebases + pushes |
| Law file | Clone root: `CANONICAL_LAW.md` |

**Manual:**

```bash
bash .cursor-commands/ops/scripts/backup_to_github.sh
```

**Automatic (every session end):**

1. `sessionEnd` hook → `ops/hooks/session_end_governance_backup.sh`
2. Gate: `ops/scripts/backup_gate.sh` decides whether this firing is a real
   boundary. `sessionEnd` fires once per composer conversation — including
   aborted chats and window closes — so the hook is filtered, debounced
   (`GOVERNANCE_BACKUP_MIN_INTERVAL`, default 900s) and held off while the
   working tree is still being written (`GOVERNANCE_BACKUP_QUIET_SECONDS`,
   default 120s). A skip is logged, never silent.
3. Log: `~/.cursor-governance/backup.log`

Skip one session: `GOVERNANCE_BACKUP_SKIP=1`
Bypass the gate for one run: `GOVERNANCE_BACKUP_FORCE=1` (a manual
`backup_to_github.sh` / `make backup` never touches the gate at all)

---

## 6. Skill Wiring

- New global skill → `l9-skill-compiler`, then `l9-wire-skill-into-repo`
- New repo-local skill → `.claude/skills/plasticos-*` (not governance root)
- **Deprecated skills cannot remain in live `skills/`.** Archive with
  `git mv skills/<name> skills/_archived/<name>`, remove from
  `AUTONOMY_MANIFEST.yaml` tiers, and keep them out of adapter reconcile /
  skill-registry generation. `status: deprecated` or `*-deprecated` at the
  top level of `skills/` is a fail-closed sync error.

## 6.1 Autonomy Velocity Doctrine (adapter surfaces)

SSOT fragment: [`ops/autonomy/surface_profile.yaml`](ops/autonomy/surface_profile.yaml).

When `L9_AUTONOMY_ENABLED=true` and `L9_GOVERNANCE_SURFACE` is an LLM adapter
(`claude-code`, `codex`, `gemini`, `manus` — **not** `cursor`):

| Action | Default |
|--------|---------|
| Scoped commit / push on feature branches | Autonomous — no per-action ask |
| Create / update PR | Autonomous |
| Load + run `l9-pr-remediation` after PR exists | Autonomous **behavior** (skill stays explicit-only) |
| Multi-lane campaign | `/autonomy` + runtime |
| Merge / force-push / hard-reset / secrets | Forbidden; merge denied by `ops/autonomy/merge_gate.py` |

**Authority order (adapters):** CANONICAL_LAW (this section + Profile) → ADR-0001 →
settings allow/deny + merge_gate → AGENTS.md → skills → **agent-invented contracts (lowest)**.

<!-- CURSOR_AUTO_LOCAL_COMMIT_V1 -->
Cursor **must** scoped-commit authored work without asking (pathspecs;
rule 49; `99-no-auto-commit`). Ask-first applies to **push / PR open**
only. Operator 2026-08-22.
Deploy settings via `ops/scripts/reconcile_claude_settings.py` (`make claude-settings`).
Do not fork Profile prose into SessionStart/README/ADR — cite the Profile.

<!-- CURSOR_COMMIT_BEFORE_STOP_V1 -->
`99-no-auto-commit` is always on. Filename = no auto-push. Unique dirty
files the agent authored this session are a rule failure. Ask only before
push / `make pr`. Operator 2026-08-27.

## 6.2 L4 Local Autonomy (no mid-execution push)

SSOT fragment: [`ops/autonomy/surface_profile.yaml`](ops/autonomy/surface_profile.yaml)
(`l4_local_autonomy`). Mechanical gate:
[`ops/autonomy/local_execution_gate.py`](ops/autonomy/local_execution_gate.py) —
**which does not gate `git` or `gh`; see §6.2.4**. Effect-plane gate:
[`ops/autonomy/git_guardrails.py`](ops/autonomy/git_guardrails.py). Phase CLI:
[`ops/autonomy/l4_local.py`](ops/autonomy/l4_local.py).

Standing doctrine for program/contract execution (default **ON**;
`L9_L4_LOCAL_AUTONOMY=1`):

| Phase | Allowed | Denied |
|--------|---------|--------|
| Local execution on stacked feature branch | Local commits | `make push`, MCP `create_pull_request` / `push_files`, mid-exec remote (see §6.2.4 for `git`/`gh`) |
| Post-finish kernels | Run `kernels/Recursive Alignment.md` then `kernels/Validate & Repair.md` | Claiming release without both kernels |
| `release_authorized` (receipt) | Scoped push + PR using `PULL_REQUEST_TEMPLATE.md` | Mid-exec remote / force-push / secrets |
| Post-push | `l9-pr-remediation` Converge; resolve review threads; merge when user-authorized | Standing merge without user auth; force-push |

Agents MUST NOT stall for push-approval pacing mid-execution. Finish locally →
kernels → `authorize-release` → push scoped PRs → remediate to green → resolve
reviews → merge when user authorizes. Older open PRs: remediate and merge
**bottom-up** by `createdAt` before newer tips. Breakglass:
`L9_LOCAL_PUSH_AUTHORIZED=<reason>` or `L9_L4_LOCAL_AUTONOMY=0`. Explicit merge
auth: `L9_MERGE_AUTHORIZED=<reason>`.

<!-- KERNEL_PRECOMMIT_HOOK_V1 -->
Post-finish kernels are **not** an L4 phase. `authorize-release` does not
require kernel stamps. `ops/autonomy/kernel_gate.py precommit` is the first
step of `make precommit-repo` / `make pr-check` and fails closed before any
other hook or test. Apply Alignment then Validate & Repair only when that
hook says so; then re-run the same gate once.

---

## 7. Anti-Patterns

- Second governance tree in any repo
- Hard-resetting or force-pushing the SSOT clone
- Committing `.cursor-commands` symlink target into app repos (symlink only; content lives in `~/.cursor-governance`)
- Referencing archived scripts (`ops/scripts/_archived/`) as active dependencies
- Leaving deprecated skill packs under live `skills/<name>/` (must live under `skills/_archived/`)
- Using `cursor_memory_client.py` — deprecated, use Graphiti
- "Fire and hope" command execution — issuing a write/execute command with no prior read-only diagnosis (see §11)
- Implementing shared cross-surface capability under a dependent adapter (e.g. `environment/claude-code/` or `environment/agents/adapters/claude-code/`) and wrapping Cursor to import it — violates §2.1; causes adapter spaghetti

---

## 8. Memory Layer (Graphiti-Native)

| Layer | SSOT | Interface |
|-------|------|-----------|
| Durable episodes | Graphiti (Neo4j on VPS) | `intelligence/context-memory/graphiti_sink.py` |
| Graph query | Graphiti (Neo4j on VPS) | `intelligence/context-memory/show_context_graphiti.py` |
| Local cache | `intelligence/context-memory/sessions/*.json` | Fallback only |
| MCP interface | `ops/graphiti/graphiti_memory_client.py` | L9-Ops-MCP |

**Rules:** `03-graphiti-memory.mdc`, `97-graph-layer-boundary.mdc`, `98-graphiti-memory-gate.mdc`, `99-graphiti-temporal.mdc`
**Skill:** `skills/l9-graphiti-memory/SKILL.md`
**Flags:** `GRAPHITI_MEMORY_ENABLED`, `GRAPHITI_WRITE_GATES`

Session start prefetch: `ops/hooks/session_start_memory_orchestrator.sh`

### Single front door (ADR-0006)

- Lifecycle + interactive MCP: Graphiti only (`graphiti_memory_client.py`, tunnel `:8100`)
- Claude/Manus/Codex adapters: **thin wrap** — never a second HTTP memory plane
- Forbidden residue: `L9_MEMORY_HTTP_URL`, `L9_MEMORY_CLIENT_TOKEN`,
  `environment/claude-code/memory/memory_client.py`, `l9-shared-memory` @
  `memory.quantumaipartners.com`, `L9_MEMORY_ENFORCEMENT=off`
- Operator-only back door: `L9_MEMORY_ENFORCEMENT_BREAKGLASS` (admin; not agent-settable)

### Deprecated (archived)

- `cursor_memory_client.py` — replaced by `graphiti_memory_client.py`
- `environment/claude-code/memory/memory_client.py` — HTTP side door removed (ADR-0006)
- `learning_to_mcp_bridge.py` — archived
- All `install_*.sh` scripts (except `install_export_job.sh`) — archived
- All recursive learning daemon scripts — archived

---

## 9. Intelligence & Signal Mining

The `intelligence/` directory is a **permanent, active signal corpus**. All data within it — including exported chats, logs, reasoning traces, and meta-learning artifacts — is valuable and will be mined for knowledge graph enrichment.

**Active mining scripts (do not archive):**
- `ops/scripts/export_chats.sh`
- `ops/scripts/parse_chat_exports.py`
- `ops/scripts/transcript_distiller.py`
- `ops/scripts/run_distiller.sh`
- `ops/scripts/install_export_job.sh`
- `ops/graphiti/hydration/openai_fixed_host.py` — Sonar-clean Phase B / worker transport
- `ops/graphiti/distill_queue/` — SessionEnd enqueue + GHA worker (redacted excerpts only)

---

## 10. Governance Enforcement

| Flag | Purpose | Default |
|------|---------|---------|
| `GOVERNANCE_HARDENING_ENABLED` | Lock production environment | `false` |
| `GOVERNANCE_BACKUP_SKIP` | Skip one session backup | `false` |
| `GOVERNANCE_SYNC_HARD_RESET` | Allow hard reset on sync (dangerous) | `false` |
| `GRAPHITI_MEMORY_ENABLED` | Enable Graphiti memory layer | `true` |
| `GRAPHITI_WRITE_GATES` | Enable write-through to graph | `true` |

---

## 11. Diagnose-First Execution Discipline

**Source kernel:** `WIP/Diagnose First Kernel.md` — full principles, allowed/forbidden actions, enforcement sequence.
**Related, not duplicate:** ADR-0072 "Diagnose Before Fix" (`WIP/0072-diagnose-before-fix.md`) governs root-cause diagnosis of an existing *error*. This section governs diagnosis of current *state* before any command is proposed — diagnostic commands always precede execution commands. Applies to infra, secrets, config, deploys, and any CLI/tool invocation that changes state — not limited to one tool or platform.

**Law:** No write/execute command may be proposed or run until current state has been inspected read-only and summarized from trusted sources. No "fire and hope."

### Enforcement sequence (binding order)

| Step | Requirement |
|------|-------------|
| 1. Read state | Run read-only inspection (config validate/get, secret *shape* only — never values, schema lookup) before any plan is proposed |
| 2. Plan changes | Present an explicit diff-style plan (path → old value shape → new value shape); get user confirmation if risk > low |
| 3. Write changes | Execute only commands matching the approved plan; touch no path beyond it |

### Forbidden

| Pattern | Why |
|---------|-----|
| Write-before-read | Any config `set`/`patch`/`unset` or infra write issued before a corresponding read/validate step in the same session |
| Placeholder commands | Angle-bracket placeholders, ALL_CAPS stand-ins, or fake values (`<...>`, `YOURUSERID`, `EXAMPLE`, `foo`) in a command presented as ready to run |
| Secret duplication | Copying secret values out of their source-of-truth vault (e.g. AWS Secrets Manager) into local config when a reference/pointer pattern is available |
| Inferring missing state | Guessing an unknown required value instead of asking the user |

### User preferences (locked)

`zero_ambiguity_tolerance`, `copy_paste_ready_commands_only`, `diagnose_before_execution`, `no_placeholders`, `ask_if_unknown` — all `true`.

---

## 12. Mandatory Pre-PR Local Gate (`make pr`)

**Law:** No pull request may be opened — and no CI triggered by opening or
updating one — until the local changed-files pre-commit pipeline has passed on
the draft. From the repo root, before you open the PR:

```bash
make pr        # alias: make pr-check — changed-files pre-commit + ruff + security
```

**Fail-closed.** If `make pr` exits non-zero: fix the findings and re-run. Do
**not** open the PR, do **not** push to trigger CI, and **never** bypass the gate
to "let CI catch it." CI is the second line of defence, not the first.

| Rule | Detail |
|------|--------|
| Target | Lowercase `make pr` (alias `make pr-check`). Make targets are case-sensitive; `make PR` is not a target and errors. |
| Target (corrected 2026-08-14) | Supersedes the row above: the Makefile now remaps any capitalization, so `make pr` / `make PR` / `make Pr` / `make pR` all run the same gate (`AGENTS.md` §6). The original row is retained because this file is append-only. |
| Target (corrected 2026-08-16) | `make pr` is the sole agent/operator PR shipping command. Do not run a separate gate-only pass. The original alias row is retained because this file is append-only. |
| Scope | CHANGED FILES ONLY (`AGENTS.md` §2.3 invariant). Full-tree is `make pr-full` / `make precommit` — intentional/nightly, and never a substitute for `make pr`. |
| Applies to | Every L9 / Quantum-L9 coding workspace and every agent surface (Cursor, Claude Code CLI · Web · Mobile, Codex, Gemini, …). |
| Authority | Non-optional. Sits above per-session context in the authority order; enforced operationally in `AGENTS.md` §6. |

### Anti-pattern: Keychain / Chrome cookie decrypt for UI automation

Do **not** use macOS Keychain or daily-Chrome Safe Storage / cookie decrypt as
the primary auth path for governed SaaS UI automation. Resolve secrets by ref
via `ops/secrets` + skill `l9-aws-secrets` (AWS Secrets Manager,
`openclaw-igorbot/*`). UI sessions use provisioned `ui-session-*` refs when
needed — never commit `storage_state` blobs.

---

## 13. Integration Branch & Local Runtime Discipline

**Law (multi-environment app repos):** When a consumer repository declares an
integration branch and a production branch (e.g. PlasticOS `Staging` /
`Production`), **all product work must hit the integration branch first** via
PR. Production is a promote-from-integration path only — never a feature-PR
target. Ship-intended work must not remain only in local tips, stashes, or
deleted remotes without an open or merged integration-branch PR.

**Law (local runtime before remote shell):** When a repository declares a local
full-stack runtime (PlasticOS: Docker Compose via `make up` / `make test-odoo` /
`make test-module` / `make install-smoke`), that runtime is the **primary**
develop–debug–fix loop. Agents must run it when the operator asks for e2e /
Docker / full proof, and when the agent judges runtime proof necessary. Remote
PaaS shells (e.g. Odoo.sh) are for diagnosis and deploy confirmation — not for
inventing fixes that are reverse-integrated into git afterward.

| Principle | Requirement |
|-----------|-------------|
| Integration-first | Feature/fix/docs/test PRs → declared integration branch only |
| No lost work | Remote branch + integration PR (draft OK) for ship-intended WIP |
| Local runtime primacy | Prove in declared local stack before remote shell hotfixes |
| Honesty | If required runtime was unavailable, report `NOT RUN` — never fake green |

**Repo overlays** may tighten (never weaken) this law. PlasticOS SSOT:
`IB-Odoo_19/.cursor/rules/72-plasticos-staging-first-docker-law.mdc`.

<!-- PROGRAM_EXECUTION_ADAPTER_LAYER_V1:CANONICAL_LAW -->

## Program Execution subsystem

`environment/program-execution/` is the canonical Program Execution subsystem.
Its sealed `core/` owns program-level truth, Program Locks, Controller state law,
and canonical worker and verification receipts. Root `autonomy/` is a subordinate
local enforcement provider, not a second Program Execution Controller.

Program Execution adapters may narrow authority but must never widen it. Mutable
program runtime, leases, attempts, receipts, and health state live outside this
repository under `$HOME/.l9/programs/`.

---

## 14. Openclaw GitHub PAT Authority (no human GitHub UI)

**Law:** For any Quantum-L9 GitHub API / `gh` / org-admin / workflow-file /
seed / PR / issue operation that a credential can perform, agents **MUST**
authenticate with the registered AWS secret ref

```text
openclaw-igorbot/github#token
```

resolved via `ops/secrets` + skill `l9-aws-secrets` (typically exported as
`GH_TOKEN` / `GITHUB_TOKEN` for the duration of the command). This is why
openclaw was given access: **agents share that authority** and must exercise it.

| Rule | Detail |
|------|--------|
| Single PAT | **Do not** create a second “cursor” / “agent-admin” GitHub PAT in AWS while `openclaw-igorbot/github#token` works. Rotate that secret in place if scopes change. |
| No human GitHub UI | Agents **MUST NOT** ask the human to operate `github.com` UI (App install accepts, permission review clicks, settings toggles, manual secret paste into Actions UI, etc.) when the openclaw PAT (or an already-wired App credential in AWS/Actions) can complete the same outcome via API/`gh`. |
| Prefer API outcome | If a GitHub App install lacks a permission (e.g. `workflows`), use the PAT (which includes `workflow` scope) to perform the file/API mutation, or fix the App via API when available — **do not** stop and send the human to an Installations settings URL. |
| Secrets SSOT | Namespace remains `openclaw-igorbot/*` in AWS SM (`us-east-1`). No parallel `cursor-secrets` inventory. Values never in git, chat, or receipts. |
| Already-wired App env | `GOVERNANCE_APP_ID` / `GOVERNANCE_APP_PRIVATE_KEY` on `Quantum-L9/.github` environment `governance-distribution` are for Actions `create-github-app-token` (seeder). Agents still use the openclaw PAT for interactive/`gh` authority; do not demand a duplicate App PEM in chat. |
| Ask-human exception | Only after `resolve_secret.py --check` fails (`UNREGISTERED` / `NOT_PROVISIONED` / `NOT_FOUND` / AWS auth broken), or for true non-API human factors (physical 2FA device, legal acceptance the API cannot perform). Name the failing ref. |

**Authority order note:** This section outranks agent-invented “I need you to click GitHub” contracts. It does not authorize merge-to-`main` bypass, force-push, or secret exfiltration — those remain forbidden under §6.1 / autonomy merge gate.

**§14 added:** 2026-08-11 (Openclaw GitHub PAT authority — no human GitHub UI).

<!-- L4_PROGRAM_BUILD_IMPLIES_MERGE_V1 -->
## 6.2.1 Program/plan Build implies merge (2026-08-12) — supersedes §6.2 merge phrasing

Launching a program or clicking Build on a plan **is** merge authorization for
that stack. Agents MUST NOT wait for a separate merge ask after remediation
reaches green + mergeable. Older open PRs: remediate and merge **bottom-up** by
`createdAt` before newer tips. Mechanical gate: `ops/autonomy/merge_gate.py`
allows ordinary `gh pr merge` when a valid L4 release receipt authorizes the
stack (or `L9_MERGE_AUTHORIZED=<reason>`). Force-push, hard-reset, and
admin-merge remain forbidden.

<!-- CONTEXT_SENSITIVE_GIT_GUARDRAILS_V1 -->
## 6.2.4 Git is gated by effect, not by name (2026-08-21) — supersedes §6.2 push-denial phrasing

`git` and `gh` are **not** denied by `ops/autonomy/local_execution_gate.py`, and
have not been since 2026-08-18. Older text saying otherwise names an enforcement
that does not exist; do not treat it as live.

Two planes, and only one of them denies:

1. **Workflow plane — preference, not enforcement.** `make pr` is the preferred
   route to GitHub: it is the only one that runs the checkers. `git` and `gh` are
   exempt from every workflow denial — publish-path, L4 phase, worktree isolation
   — via [`ops/autonomy/git_execution_exemption.py`](ops/autonomy/git_execution_exemption.py).
   The classifiers still *report* a raw publish, so a policy engine can say "you
   bypassed `make pr`" after the fact. That report is not a block.
2. **Effect plane — this one denies.** Every shell command is first evaluated by
   [`ops/autonomy/git_guardrails.py`](ops/autonomy/git_guardrails.py) (contract
   `l9-context-sensitive-git-guardrails`), which decides from the command's actual
   effect, the sensitivity of its target, and provable recoverability. Read-only
   git is allowed unconditionally; a destructive primitive over disposable state
   is allowed; an unrecoverable mutation of sensitive state is denied — to a
   human, not to a workflow phase.
**Correction (2026-08-28): read "two planes" above as THREE, two of which deny.**
A third plane was added below. The count in the sentence above is preserved
rather than edited, because this document supersedes by appending — the same way
§6.2.4 supersedes §6.2's push-denial phrasing without rewriting it.

3. **Verification plane — this one denies too.** Every shell command is also
   evaluated by [`ops/autonomy/verification_bypass_gate.py`](ops/autonomy/verification_bypass_gate.py)
   (contract `l9-commit-verification-integrity`), which denies commands that skip
   the hooks verifying a commit: `git commit --no-verify` / `-n`,
   `git push --no-verify`, `core.hooksPath` overrides, hook-suppressing env vars
   on a commit, `pre-commit uninstall`, and writes under `.git/hooks/`. Forms are
   declared in [`ops/config/commit-verification-contract.json`](ops/config/commit-verification-contract.json);
   human/ops breakglass is `L9_VERIFY_BYPASS_AUTHORIZED=<reason>`. This narrows
   nothing in plane 1: a plain `git push` is **not denied**, and neither is
   `gh pr create`. Only the hook-skipping *form* is refused, never the command.

   It runs at the same point as the effect plane — **before** the exemption — for
   the same structural reason: a check in the workflow plane never sees a git
   command. It is separate from the effect plane because that contract reasons
   about *destroying work*, and skipping a hook destroys nothing, it removes a
   check. Two questions, two contracts.

   This does not restore name-based gating. The denial is not "the word
   `--no-verify` appeared": value-taking flags are skipped so `git commit -m "-n"`
   is allowed, `git push -n` (`--dry-run`) is allowed, and `SKIP=... pre-commit run`
   — how `run_pr_precommit.sh` narrows the sanctioned gate — is allowed. Publishing
   itself is **not denied** here either. What this plane refuses is the *effect* of
   writing a commit without the verification that governs it.

Still mechanically denied at every phase, including `release_authorized`, because
they reach GitHub without the checkers: `make push`,
`mcp__github__create_pull_request`, `mcp__github__push_files`. Force-push,
hard-reset, admin-merge and secret exfiltration remain forbidden under §6.1.

The permission layer must agree. `environment/agents/adapters/claude-code/validate_claude_env.py`
**fails the build** if `permissions.deny` carries any `Bash(git …)` / `Bash(gh …)`
entry, because blocking at the permission layer what enforcement deliberately
allows is the same split-brain mirrored. Policy may discourage a command; the
permission layer must not block it.

Rationale: naming commands cannot distinguish `git push` to a feature branch from
`git push --force` over a colleague's work. Effect can. Enforcing by name gave
both a false sense of protection and, in this repository, a constitution that
described a gate its own code had stopped implementing.

The verification plane was added (2026-08-28) after the mirrored failure: eight
skill files forbade `git commit --no-verify` and every gate allowed it, while
five workflow executors emitted it. Doctrine without enforcement is the same
split-brain as enforcement without doctrine — it just fails quietly instead of
loudly. A prohibition that no process can refuse is a preference.

<!-- GOVERNANCE_ACTIVATE_FRESH_SESSIONSTART_V1 -->
## 5.1 SessionStart tip activation + symlink notes (2026-08-12) — supersedes §2 / §5 rows

Authoritative corrections (do not treat older table rows above as SSOT where
they conflict):

| Item | Value |
|------|-------|
| `.cursor-commands` | Consumers only — **never** on the SSOT clone itself |
| `.cursor/plans` | Convenience link to `~/.cursor/plans` (not governance SSOT) |
| Activate (session start) | `governance_activate_fresh.sh` — foreground tip authority (ff-or-swap); STATUS line + receipt |
| Manual sync | `governance_sync.sh` — guarded ff-only pull + optional push-half (not used for sessionStart pull) |
| Post-hook state | sessionStart `additional_context` — sectioned L9 session state (Governance / Runtime / Graphiti hydrate stats / Code-graph); no memory-bank |

<!-- L9_PLAN_SLASH_RETIRE_V1 -->
## Executable plan slash command (2026-08-12) — supersedes §1 table `/plan` wording

Authoritative correction (do not treat the older **Executable plan template**
table cell above as SSOT where it conflicts):

1. Slash `/plan` is **retired**. Use `/l9-plan` (command `commands/l9-plan.md`)
   and skill `l9-plan` v4+.
2. Default projection remains
   `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`
   via PE+autonomy (`references/plan-workflow-pe-autonomy.md`).
3. `.cursor/plans/_TEMPLATE.plan.md` stays a local mirror only (sync via
   `skills/l9-plan/scripts/sync_cursor_plan_template.py`).

<!-- SESSIONEND_PHASE_B_DISTILL_V1 -->
## 9.1 SessionEnd Phase B distill queue (2026-08-12) — supersedes §9 mining-script notes

Authoritative corrections (do not treat older §9 bullets above as SSOT where
they conflict):

1. `ops/scripts/transcript_distiller.py` is a thin wrapper → Graphiti S3 queue
   worker (`ops/graphiti/distill_queue/`); C1 `save_memory` / Dropbox LaunchAgent
   retired.
2. `ops/scripts/run_distiller.sh` is the local operator entry to the same worker;
   batch schedule is GHA `.github/workflows/memory-distill.yml` (not Mac 5am cron).
3. Active additive paths under §9: `ops/graphiti/hydration/openai_fixed_host.py`
   (Sonar-clean Phase B / worker transport) and `ops/graphiti/distill_queue/`
   (SessionEnd enqueue + GHA worker; redacted excerpts only).

<!-- CHAT_TRANSCRIPT_S3_ARCHIVE_V1 -->
## Closed-chat word archive (2026-08-13) — supersedes §9 `export_chats.sh` / mining dumps

Authoritative corrections (do not treat older §9 “do not archive” bullets as SSOT):

1. `ops/scripts/export_chats.sh`, `parse_chat_exports.py`, `install_export_job.sh`,
   and `process_learnings.sh` are **retired**. Hourly sqlite/txt dumps and the
   tenx `com.tenx.learning-processor` → `memory_aggregator.py` Dropbox path are
   retired. See `ops/scripts/RETIRED_export_chats_and_learning_processor.md`.
2. When a chat is X'd out (`sessionEnd`), the **words** (user/assistant text)
   plus timestamps/meta are archived to S3
   `l9-chat-transcripts-020125249784` key `v1/<conversation_id>.json`.
   No sqlite, no tool dumps, no git_status noise. Cross-machine SSOT is S3,
   not GitHub and not a local disk.
3. Graphiti distill queue remains **excerpts only** for memory. Full words for
   later mining live in the transcript bucket.
4. Operator: `python -m ops.graphiti.hydration.archive_transcript`
   (`--session-id` or `--backfill`). Env `L9_CHAT_TRANSCRIPT_S3_BUCKET`.

<!-- DIAGNOSE_FIRST_KERNEL_PATH_V1 -->
## Diagnose First kernel path (2026-08-14) — supersedes §11 Source kernel line

Authoritative correction (do not treat the older §11 **Source kernel** path as SSOT
where it conflicts):

1. Full Diagnose First kernel SSOT is
   `WIP/backlog/kernels/diagnose-first/Diagnose First Kernel.md`.
2. The older pointer `WIP/Diagnose First Kernel.md` is absent on tip — do not use it.
3. `prompts/10X Kernels/Diagnose First Kernel.md` remains a short digest only, not §11 SSOT.
4. Skill `l9-git-work-preserve` / slash `/git-work-preserve` bind the backlog full kernel.

<!-- RULES_CORPUS_CLEANUP_GRAPHITI_REFS_V1 -->
## Graphiti rule refs after corpus cleanup (2026-08-14) — supersedes §8 Rules line

Authoritative correction (do not treat the older §8 **Rules** stem list as SSOT
where it conflicts):

1. `99-graphiti-temporal.mdc` was **deleted** in rules-corpus-cleanup-v1; temporal
   supersedes/conflicts live inside `03-graphiti-memory.mdc`.
2. Live §8 rule set: `03-graphiti-memory.mdc`, `97-graph-layer-boundary.mdc`,
   `98-graphiti-memory-gate.mdc` (plus skill / flags unchanged).

<!-- DIAGNOSE_FIRST_KERNEL_PATH_V2 -->
## Diagnose First kernel path (2026-08-14) — supersedes the WIP backlog path

Authoritative correction (do not treat the older 2026-08-14 **WIP/backlog**
Diagnose First path as SSOT where it conflicts):

1. Full Diagnose First kernel SSOT is `kernels/Diagnose First Kernel.md`.
2. The 2026-08-14 pointer
   `WIP/backlog/kernels/diagnose-first/Diagnose First Kernel.md` is retired —
   do not restore that path.
3. `prompts/10X Kernels/Diagnose First Kernel.md` remains a short digest only,
   not §11 SSOT.
4. Skill `l9-git-work-preserve` / slash `/git-work-preserve` bind
   `kernels/Diagnose First Kernel.md`.

<!-- CAMPAIGN_EXECUTION_PR_NO_MERGE_V1 -->
## 6.2.2 Campaign execution: make pr, no remediate, no merge (2026-08-14)

Supersedes §6.1 remediation row, §6.2 post-push merge phrasing, and §6.2.1
(program/plan Build implies merge) for agent action:

1. Required publish path after L4 release: `PR_REMEDIATE=0 make pr`.
2. Agents MUST NOT spawn `l9-pr-remediation` or merge. An L4 release receipt
   does **not** authorize `gh pr merge`. Human only: `L9_MERGE_AUTHORIZED`.
3. Program Execution campaigns land on `campaign/<campaign_id>` and MUST set
   `PR_BASE` to that branch. Opening those PRs against `main` is forbidden.
4. SSOT: `ops/autonomy/surface_profile.yaml` (`campaign_execution`) and
   `environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml`.

<!-- PR_REMEDIATION_AUTHORIZES_MERGE_V1 -->
## 6.2.3 /l9-pr-remediation authorizes merge (2026-08-16)

Supersedes §6.2.2 “MUST NOT … merge” for the remediations skill only:

1. Campaign / `make pr` path still does not merge. End state is green +
   merge-ready PRs on the campaign integration branch.
2. Invoking `/l9-pr-remediation` writes
   `ops/autonomy/authorize_merge.py --all-open` and then merges every
   green mergeable open PR in the target repo (bottom-up, no `--admin`).
3. Mechanical gate: `ops/autonomy/merge_gate.py`. Force-push / hard-reset /
   admin-merge remain never-waived.

<!-- SSOT_CHECKOUT_CONSUMER_WIRING_V1 -->
## 1.1 SSOT-family checkouts are not consumers (2026-08-17)

Append-only clarification of §1. Do not treat a checkout of this repository
as a product consumer that must present `.cursor-commands`.

1. `.cursor-commands` → `$HOME/.cursor-governance` is the **consumer** entry.
2. Workspace kinds (`ops/scripts/lib/workspace_kind.sh`):
   - `ssot` — `realpath(workspace) == realpath($HOME/.cursor-governance)`.
     `.cursor-commands` must be absent (no self-alias).
   - `ssot_checkout` — this repo’s identity files at the workspace root
     (`CANONICAL_LAW.md`, `skills/AUTONOMY_MANIFEST.yaml`,
     `rules/RULES-MANIFEST.yaml`, `ops/scripts/check_governance_wiring.sh`)
     and the path is not the live SSOT. Worktrees and second clones qualify.
     Do **not** key off `$HOME/.l9/gov-worktrees/` alone.
   - `consumer` — everything else. Missing `.cursor-commands` still fails.
3. `make pr` / `symlinks-check` on `ssot` or `ssot_checkout` must not require
   `.cursor-commands`, `.cursor/plans`, `.cursor/governance`, or an IDE
   profile stamp. Machine-global hooks stay fail-closed. SSOT tip / dirty /
   unpushed is WARN-only on `ssot_checkout`.

## 8.1 Memory does not gate repository mutation (2026-08-18) — supersedes §8 phase-lock wording

The **L9 Multi-Agent Main-Bound Execution Contract**
(`rules/96-multi-agent-main-bound-execution.mdc`) is binding for every agent
performing repository mutation. It separates authorities that must never be
substituted for one another:

| Concern | Authority |
|---|---|
| Shared knowledge | Graphiti / canonical L9 memory |
| Repository isolation | dedicated git worktree |
| Canonical task ancestry | fetched `origin/main` |
| Publication | sanctioned `make pr` path |
| Collision detection | git diff + `merge-tree` + CI |
| Integration | PR merge into `main` |

Consequences that supersede earlier §8 phrasing:

1. A Graphiti phase-lock MUST NOT authorize, deny, or serialize ordinary
   repository mutation. `gmp:phase_lock` is not write permission.
2. Agent-facing `--force` memory-lock functionality MUST NOT exist;
   `environment/agents/adapters/claude-code/hooks/memory_lock.py` is removed.
3. The only permitted memory gate is fresh-hydration
   (`memory-enforcement.contract.json` v2.0.0).
4. Ordinary tasks start via `ops/scripts/agent_worktree_start.sh` from fetched
   `origin/main`; publication refreshes main and fails closed when the collision
   state cannot be determined.

Memory conflicts remain useful evidence. They are not repository locks.

<!-- CURSOR_PLANS_REPO_STORE_V1 -->
## Cursor plans store (2026-08-20) — supersedes §5.1 `.cursor/plans` row

Authoritative corrections (do not treat the older “not governance SSOT” cell
as the live store):

1. Tracked store: `<gov-checkout>/docs/plans/`.
2. `~/.cursor/plans` → that directory. Workspace `.cursor/plans` →
   `~/.cursor/plans` (unchanged hop).
3. Heal helper: `ops/scripts/lib/cursor_plans_store.sh`. Stamp:
   `$HOME/.cursor/l9-plans-store`.
4. `.cursor/plans/_TEMPLATE.plan.md` still syncs via
   `skills/l9-plan/scripts/sync_cursor_plan_template.py`; it now lands in
   `docs/plans/` through the home symlink.

<!-- TESTS_ONCE_AND_PUBLISH_V1 -->
## 6.2.5 Tests once, then `make pr` remediates (2026-08-28)

Append-only. Supersedes §6.2.2 item 1 (`PR_REMEDIATE=0 make pr`) and the
standing “no remediate” campaign phrasing for publish only. Merge still
requires `/l9-pr-remediation` (§6.2.3). Do not edit the older lines.

1. **Tests run once locally.** Same worktree digest + `PR_BASE` → one pytest
   pass. `make pr` runs the gate. `make pr-check` then `make pr` on an
   unchanged tree is a teaching failure; receipt skip is the mechanical
   once-only. Full corpus stays `make pr-full` / nightly / push-to-`main`.
2. **Commit finished work when it is completed.** Same as
   `CURSOR_COMMIT_BEFORE_STOP_V1`. Intermediate commits do not start the
   publish gate.
3. **If the work is done and committed, `make pr`.** Default remediates is
   1, including campaign PRs. `PR_REMEDIATE=0` is opt-out only. Remediates
   means poll to green + merge-ready. Merge still requires
   `/l9-pr-remediation` Converge / `authorize_merge.py`.

<!-- PR_CHECK_FOLDED_V1 -->
## 6.2.6 `pr-check` is the internal leaf, not a public verb (2026-08-28)

Append-only. Supersedes §6.2.2 alias copy (`make pr` as `make pr-check`)
and §6.2.5 item 1's leftover `make pr-check` then `make pr` sequence.
Do not edit the older lines.

Public ceremony is `make pr`. Diagnose is `OPEN_PR=0 make pr`. Do not
type `make pr-check`. The Make target stays as the INTERNAL leaf
(`pr: pr-preflight pr-check`). Remediator verify stays
`make precommit-repo`.
