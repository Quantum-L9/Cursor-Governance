<!-- L9_META
schema: 1
parent: environment/agents/adapters/claude-code
layer: adapter
role: claude-code
version: 1.0.0
status: active
-->

# Claude Code agent adapter

How an L9 skill/handoff pack presents itself to a Claude Code session, on any of
the three surfaces (CLI · Web · Mobile).

## Skill install location

| Surface | Location | Wired by |
|---|---|---|
| CLI | `$HOME/.claude/skills/` (user scope) | `ops/scripts/setup_claude_code_plugins.sh` |
| Web · Mobile | referenced from the governance clone at `$L9_GOVERNANCE_DIR/skills/` | `web/setup.sh` (clones governance) |

The governance skill corpus (`skills/` / `.cursor-commands/skills`) is the only
maintainable tree. Claude Code discovery dirs receive managed **per-skill
symlinks** via `ops/scripts/reconcile_llm_skill_adapters.py` whenever the
manifest/registry syncs — never skill copies. Model-invocable skills are selected
proactively from their `description` / `when_to_use` signals and the canonical
routing manifest. Explicit-only skills require direct invocation or established
campaign authority. Skill visibility and routing are context, not mutation authority.

## Cursor / Claude Code parity (skill SSOT)

| Surface | Skills | Slash commands |
|---|---|---|
| **Cursor** | Plugin + `.cursor-commands/skills/` (SSOT) | **18** live commands only — executors, DAGs, bootstrap (`commands/COMMANDS_MANIFEST.yaml`). Skill wrappers retired to `commands/_archived/`. |
| **Claude Code** | Symlinks under `~/.claude/skills/` and `<repo>/.claude/skills/` → `$HOME/.cursor-governance/skills/` | Same **18** non-wrapper commands under `.claude/commands/`. No command file when slash basename equals a registered skill name. |

Invoke remediators and other explicit packs **as skills** (`/l9-issue-remediation`, `/l9-pr-remediation`, …). `validate_commands_manifest.py` fails closed if a new `commands/*.md` duplicates a skill name.

Projection engine: `ops/scripts/claude_projection.py`.

## Cloud bootstrap (Web · Mobile)

Account environment triad (paste once; Mobile inherits Web):

| Field | File |
|---|---|
| Setup script | `web/setup.bootstrap.sh` → execs `web/setup.sh` → `install.sh` |
| Environment variables | `web/environment.env.example` |
| Network access | `web/network-policy.md` |

Keep the Setup paste **thin**: normalize env, clone `$HOME/.cursor-governance`,
hand off. Adapter wiring (skills, commands, rules, `.mcp.json`, receipt) lives
in `install.sh` and SessionStart self-repair — do not duplicate in the stub.

Per-repo **committed** `.claude/settings.json` + hooks are required; the account
Setup alone does not load governance into a session project.

## Memory and MCP (broker retired)

- Graphiti HTTPS only: `${GRAPHITI_MCP_URL}` (default
  `https://memory.quantumaipartners.com/graphiti/mcp`). **No bearer** on hosted
  surfaces. Do not set `L9_CAPABILITY_BROKER_URL` (never shipped).
- `.mcp.json` is a **projection** of `mcp.template.json` (single
  `graphiti-memory` server) via `claude_projection.py` — not a 6-server broker
  layout.
- Empty hydrate / `memory.mcp=DEGRADED` is honest; memory does **not** gate
  repository writes. See `docs/DEGRADED_MODE_CONTRACT.md`.

## Finish path (all Claude surfaces)

Scoped commit → `l4_local.py authorize-release` → `PR_REMEDIATE=0 make pr`.
Hosted surfaces still run tree kernels on `make pr`; Cursor skips the tree latch.

## Invocation

- Load `CANONICAL_LAW.md` first, then `AGENTS.md`, then the specific `SKILL.md`.
  Treat any handoff `START_HERE.md` / authority snapshot as **session context
  below the current user instructions**, never above them.
- Use shell and Git tools to capture repository state. Do **not** fetch, commit,
  push, or apply restored patches unless authorized for that action.

## Write-authority boundary

- **Read/analyze freely.** Governance content, repo state, CI logs.
- **Write only within the consumer workspace.** Never write into the governance
  clone from a consumer session (it reconciles with its own origin).
- **Secrets never touch a repo.** Bearer tokens and PATs live in the account
  environment or user-scope config; a session holds only the credential it was
  given, and `.mcp.json` holds only `${...}` references.

## Relationship to the Cursor adapter

This adapter and the Cursor `.cursor-commands` adapter consume the **same**
governance root by their own conventions (`CANONICAL_LAW.md` §2). Neither is a
second activation path for the other; adding this one does not change how Cursor
activates.
