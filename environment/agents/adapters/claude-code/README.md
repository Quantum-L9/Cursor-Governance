# Claude Code environment (CLI · Web · Mobile)

First-class, **no-friction** activation of L9 governance for Claude Code, across
all three surfaces it runs on. This is the Claude Code **surface peer** of
`environment/ide/` (which renders the editor profile for Cursor/VS Code): same
IDE-neutral `policy.json`, a different activation adapter.

**Ownership law (`CANONICAL_LAW.md` §2.1):** Claude Code is a *dependent*
adapter. Shared capability (scorers, routers, autonomy brains) must live in
Cursor-primary / adapter-neutral homes (`ops/`, `rules/`, `skills/`). This
directory wraps those capabilities for Claude discovery — it must **not** own
them for Cursor to import.
> **Not to be confused with `profiles/`.** `profiles/*.md` shape how the LLM
> *reasons*. This directory configures the Claude Code *runtime* — how a session
> boots governance, discovers skills, reaches shared memory, and stays within
> safe write boundaries.

---

## 1. The three surfaces (and the one fact that governs them)

| Surface | Where it runs | Machine state (`~/.claude`, `~/.cursor`) | Governs activation |
|---|---|---|---|
| **CLI** | your machine / a persistent container | **persists** | user-scope `~/.claude/` **or** repo-committed `.claude/` |
| **Web** (`claude.ai/code`) | ephemeral cloud sandbox | **wiped every session** | repo-committed `.claude/` + account **environment** (Network / Env / Setup) |
| **Mobile** | the same account environment, from a phone | ephemeral, **inherits Web env** | identical to Web — no separate config |

**The one fact:** on Web and Mobile the sandbox is cloned fresh and reclaimed
after the session. **Only git-tracked files survive a clone.** So the entire
frictionless-activation story for Web/Mobile has to be carried by files that are
committed to the consumer repo — never by `~/.cursor/hooks.json` or `~/.vscode/`,
which never make it into the sandbox. That is the design axis of everything in
this directory.

This is also why the account **environment** (Network access · Environment
variables · Setup script) matters: it is the *only* non-repo carrier that Web
and Mobile both read, and because it is account-level, **Mobile inherits the Web
environment with no separate file** (`web/README.md`).

---

## 2. What activates governance, per surface

Governance content (skills, rules, commands, learning corpus) lives in this repo.
A Claude Code session needs three things: **discover the skills**, **boot the
context**, **reach shared memory** — without a human wiring step.

| Need | CLI | Web / Mobile |
|---|---|---|
| Discover L9 skills | `~/.claude/skills/` fed by `reconcile_claude_l9_skills.py` via `install.sh` (canonical native L9 skills) | governance cloned by `web/setup.sh`; skills referenced from the clone |
| Boot session context | `hooks/session_start_claude_governance.sh` via `make claude-settings` → `~/.claude/settings.json` | **same hook**, committed at `.claude/settings.json` + `.claude/hooks/` via reconcile |
| Autonomy velocity | Profile `ops/autonomy/surface_profile.yaml` + merge_gate + local_execution_gate PreToolUse | same Profile; standing A4 + L4 local (no mid-exec push); human merge |
| Reach shared memory | `mcp.template.json` → brokered `graphiti-memory` server (`${L9_CAPABILITY_BROKER_URL}/mcp/graphiti`, no bearer) | same committed `.mcp.json`; `L9_MEMORY_*` identity from the account environment |

### Proactive L9 skill discovery and routing

The governance `skills/` tree is reconciled into Claude Code's native discovery
locations as per-skill managed links:

- CLI: `~/.claude/skills/<skill>/SKILL.md`
- Web/Mobile: `<workspace>/.claude/skills/<skill>/SKILL.md`

**Doctrine SSOT:** `rules/23-l9-skill-routing.mdc` (three layers: `auto_invoke`,
`explicit_only+hint_allowed` → `explicit_hint`, `explicit_only`). Manifest:
`skills/AUTONOMY_MANIFEST.yaml`. Registry: `ops/generated/skill-registry.json`.
Shared scorer: `ops/skill_routing/` (single ingress). Adapters:
`UserPromptSubmit` + Cursor `before_submit_skill_router.py`. Recommendation never
grants mutation authority. `skillOverrides` hide explicit-only skills from ambient
Skill-tool selection; `hint_allowed` may still surface a Read recommendation.

`ops/scripts/reconcile_claude_l9_skills.py` preserves consumer-local skills and
removes only entries recorded in its managed-state file. Claude `.claude/rules`
is a directory symlink to `environment/generated/llm-rules/` (projected from
`rules/*.mdc` — never hand-edit; never mount raw `.mdc`). Validate with
`make claude-skills-check`.

### Native skills vs marketplace plugins — ownership split

Two different mechanisms feed Claude Code, and the names must not blur:

- **Canonical L9 native skills** — `install.sh` →
  `ops/scripts/reconcile_claude_l9_skills.py` (project scope, and the user-scope
  mirror). This is the mechanism that makes L9 skills available, on every
  surface including Web/Mobile.
- **Optional marketplace plugins** — `make claude-plugins` →
  `ops/scripts/setup_claude_code_plugins.sh`. Installs Claude marketplace
  packages (hookify, pr-review-toolkit, desktop-commander, context7),
  including project-scoped plugin mutations. This is an explicit **local /
  Desktop enhancement** and is **not required for Web/Mobile parity** — Claude
  mobile does not expose local-only commands such as `/plugin`, and a governed
  cloud session must not depend on them.

### Memory transport — brokered, and honest when degraded

The MCP template points `graphiti-memory` at the L9 capability broker
(`${L9_CAPABILITY_BROKER_URL}/mcp/graphiti`). The broker speaks the MCP
handshake (`initialize` / `tools/list` / `tools/call`) and maps its bounded
memory tools onto the registered capabilities — `search_memory` →
`graphiti.query`, `write_governed` → `graphiti.write_governed` — so the
Graphiti bearer stays on the trusted side and never reaches a
model-controlled surface.

A session without a verifiable platform identity (ordinary Anthropic-hosted
cloud today) gets an honest 401 from the broker: the MCP server is reported
unavailable and memory runs **DEGRADED — broker identity unavailable**. That
is the truthful posture, surfaced by the SessionStart status block. The fix
is broker identity delivery, never pasting `GRAPHITI_MCP_TOKEN` into an
environment.

### Memory identity — distinct from Cursor, shared graph

Two dimensions, kept separate on purpose:

- **`group_id` (repo namespace) — SHARED with Cursor.** Resolved per-repo from the
  git remote / `GRAPHITI_GROUP_ID` (`ops/graphiti/group_registry.yaml`). Sharing it
  is what makes memory shared; it is **not** forked per agent.
- **Writing-agent identity — DISTINCT from Cursor.** Cursor writes as `cursor_agent`
  (`ops/graphiti/config-docker-neo4j.yaml`, `${USER_ID:cursor_agent}`). Claude Code
  writes as `claude_code_agent` / `agent_id=claude-code`, under its **own** bearer
  token (a separate server principal — `claude-code-memory-client`). Claude Code
  never reuses Cursor's token and never writes under `cursor_agent`, so every
  episode stays attributable to the agent that produced it. Set via
  `USER_ID` / `L9_MEMORY_AGENT_ID` / `L9_MEMORY_SOURCE` (`web/environment.env.example`).
| Formatter ownership | the `CLAUDE.md` managed block (`ops/scripts/adapters/agentdocs.sh`) | **same** — the block is git-tracked, so it is the only ownership carrier that survives a clone |

Formatter ownership is deliberately **not** re-declared here: `render.claude.json`
records that Claude Code consumes ownership through the `agentdocs` adapter's
`CLAUDE.md` block, so `policy.json` stays the single authority and there is no
second place to drift.

---

## 3. Files

| File | Surface | Purpose |
|---|---|---|
| `render.claude.json` | all | Rendering map: how `policy.json` reaches Claude Code (peer of `render.cursor.json`). IDE-neutral policy never changes for it. |
| `settings.template.json` | all | Committable `.claude/settings.json` for a consumer repo: SessionStart hook + conservative permission + env defaults. |
| `hooks/session_start_claude_governance.sh` | all | Mobile-safe SessionStart bootstrap. Git-only, **no `~/.cursor` dependency**. Emits Claude Code `additionalContext` JSON. |
| `mcp.template.json` | all | Shared memory MCP block — brokered `${L9_CAPABILITY_BROKER_URL}/mcp/graphiti`. **Never a token, never a bearer.** |
| `web/README.md` | Web · Mobile | Install guide for the account environment (the Network / Env / Setup triad). |
| `web/network-policy.md` | Web · Mobile | Network-access decision (Full vs Custom allowlist) with the concrete allowlist. |
| `web/environment.env.example` | Web · Mobile | Environment-variables template. No credentials, no GH token — the platform proxy injects. |
| `web/setup.sh` | Web · Mobile | Setup-script template. Machine-level provisioning only: `gh`, governance clone, adapter install. |
| `hooks/session_deps_cloud.sh` | Web · Mobile | Cloud-only SessionStart dependency helper (consumer workspace toolchain + pre-commit warm), fingerprint-cached. |
| `adapters/claude-code.md` | all | Agent adapter: where skills install, how they are invoked, write-authority boundary. |
| `validate_claude_env.py` | — | Structural validator: JSON parses, no secrets committed, templates present. `make claude-env`. |

---

## 4. Wire it into a consumer repo (the whole no-friction path)

```bash
# From inside the CONSUMER repo (not from ~/.cursor-governance):
GOV="$HOME/.cursor-governance/environment/agents/adapters/claude-code"

mkdir -p .claude/hooks
cp "$GOV/settings.template.json"                  .claude/settings.json
cp "$GOV/hooks/session_start_claude_governance.sh" .claude/hooks/
cp "$GOV/mcp.template.json"                        .mcp.json      # optional: shared memory
git add .claude .mcp.json && git commit -m "chore: adopt L9 Claude Code environment"
```

Committing `.claude/` and `.mcp.json` is the point: the next Web or Mobile
session that clones this repo boots governance with **zero** manual steps. On the
CLI the same `.claude/settings.json` is picked up locally; nothing else to do.

For the account environment (Web/Mobile secrets, network, setup), follow
`web/README.md` **once** — it is account-level, so every repo and every Mobile
session inherits it.

Validate before you commit:

```bash
make claude-env        # or: python3 environment/agents/adapters/claude-code/validate_claude_env.py
```

---

## 5. Leverage / friction rationale (per the L9 kernel)

- **Friction removed:** a Web/Mobile session used to require a human to hand-wire
  network, env vars, a setup script, and memory before governance was usable.
  After adoption that is a clone + a one-time account-environment setup.
- **Reusable primitive:** `policy.json` gains a Claude Code renderer without
  changing; every future consumer repo adopts the same committed `.claude/`
  triad. One adapter, N repos.
- **Boundaries preserved:** no second activation path for Cursor, no duplicate of
  `policy.json`, no formatter-ownership fork — ownership still flows from
  `policy.json` through the `agentdocs` `CLAUDE.md` block.
- **Future nodes accelerated:** any new L9 repo, and any new Claude Code surface,
  inherits activation by copying one directory.
- **Unknowns (labelled, not fabricated):** the exact `~/.claude/settings.json`
  hook-event schema and the account-environment field names evolve with the
  Claude Code release; treat this adapter's templates as the contract and the
  live product docs (<https://code.claude.com/docs>) as the tiebreaker.

---

## 6. See also

- `environment/ide/README.md` — the editor-profile peer (Cursor/VS Code rendering).
- `CANONICAL_LAW.md` §2 — the IDE adapter model this row registers under.
- `AGENTS.md` §2 — the Cursor activation contract this mirrors for Claude Code.
- `ops/scripts/setup_claude_code_plugins.sh` — optional local/Desktop marketplace plugin augmentation (not the L9 skill mechanism).
