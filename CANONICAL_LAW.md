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
**Updated:** 2026-08-06 (Cursor-primary capability ownership — adapter wrap-out law)

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
| Claude Code (CLI · Web · Mobile) | `environment/claude-code/` — committed `.claude/` + account environment | Active (**dependent adapter**) |
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
| Shared scorer / router / autonomy brain lives under `environment/claude-code/` and Cursor imports it | Inverts ownership — Claude adapter owns Cursor’s brain |
| “Claude implemented it; wrap Cursor to reuse Claude” | Dependent adapter dictating the SSOT |
| Duplicating the same brain in each adapter folder | Drift and dual maintenance |
| Treating “peer of `environment/ide/`” as equal ownership of cross-surface logic | Peer = surface parity, not capability ownership |

**Required shape:**

| Layer | Owner | Example |
|---|---|---|
| Shared capability | Cursor-primary / adapter-neutral governance | `ops/hooks/*`, `ops/scripts/*`, `rules/*`, `skills/*`, shared libs under `ops/` |
| Cursor binding | Cursor adapter paths | `~/.cursor/hooks.json`, `l9-governance` plugin, `.cursor-commands` |
| Other LLM/IDE binding | Thin wrapper only | `environment/claude-code/hooks/*` imports shared ops; does not own the scorer |

**Skill routing ownership:** shared scoring lives in `ops/skill_routing/`;
registry at `ops/generated/skill-registry.json`. Claude and Cursor hooks are
thin I/O adapters only.

Multi-agent identity (WHO writes memory: agent IDs, roles, tokens-by-name) is
governed by `environment/agents/agent_registry.yaml` — peer of
`ops/graphiti/group_registry.yaml` (WHAT repo memory is about). Validate with
`make agents-env`. See `environment/agents/README.md`.

The Claude Code adapter is defined in `environment/claude-code/` (surface peer of
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

---

## 7. Anti-Patterns

- Second governance tree in any repo
- Hard-resetting or force-pushing the SSOT clone
- Committing `.cursor-commands` symlink target into app repos (symlink only; content lives in `~/.cursor-governance`)
- Referencing archived scripts (`ops/scripts/_archived/`) as active dependencies
- Leaving deprecated skill packs under live `skills/<name>/` (must live under `skills/_archived/`)
- Using `cursor_memory_client.py` — deprecated, use Graphiti
- "Fire and hope" command execution — issuing a write/execute command with no prior read-only diagnosis (see §11)
- Implementing shared cross-surface capability under a dependent adapter (e.g. `environment/claude-code/`) and wrapping Cursor to import it — violates §2.1; causes adapter spaghetti

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

### Deprecated (archived)

- `cursor_memory_client.py` — replaced by `graphiti_memory_client.py`
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
| Scope | CHANGED FILES ONLY (`AGENTS.md` §2.3 invariant). Full-tree is `make pr-full` / `make precommit` — intentional/nightly, and never a substitute for `make pr`. |
| Applies to | Every L9 / Quantum-L9 coding workspace and every agent surface (Cursor, Claude Code CLI · Web · Mobile, Codex, Gemini, …). |
| Authority | Non-optional. Sits above per-session context in the authority order; enforced operationally in `AGENTS.md` §6. |

### Anti-pattern: Keychain / Chrome cookie decrypt for UI automation

Do **not** use macOS Keychain or daily-Chrome Safe Storage / cookie decrypt as
the primary auth path for governed SaaS UI automation. Resolve secrets by ref
via `ops/secrets` + skill `l9-aws-secrets` (AWS Secrets Manager,
`openclaw-igorbot/*`). UI sessions use provisioned `ui-session-*` refs when
needed — never commit `storage_state` blobs.
<!-- PROGRAM_EXECUTION_ADAPTER_LAYER_V1:CANONICAL_LAW -->

## Program Execution subsystem

`environment/program-execution/` is the canonical Program Execution subsystem.
Its sealed `core/` owns program-level truth, Program Locks, Controller state law,
and canonical worker and verification receipts. Root `autonomy/` is a subordinate
local enforcement provider, not a second Program Execution Controller.

Program Execution adapters may narrow authority but must never widen it. Mutable
program runtime, leases, attempts, receipts, and health state live outside this
repository under `$HOME/.l9/programs/`.
