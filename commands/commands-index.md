---
name: commands-index
version: "2.0.0"
description: "Human index of enabled L9 Cursor Governance slash commands"
status: active
updated: "2026-08-01"
registry: commands/COMMANDS_MANIFEST.yaml
recognition_rule: rules/02-slash-commands.mdc
---

# L9 Cursor Commands — Index

Slash commands live in `commands/*.md` and activate whenever Cursor Governance is wired:

1. Plugin: `~/.cursor/plugins/local/l9-governance` → `$HOME/.cursor-governance`
2. Repo symlink: `.cursor-commands` → same SSOT
3. Bootstrap: `sessionStart` hook or `/start-session` / `make start`

Machine registry: [`COMMANDS_MANIFEST.yaml`](COMMANDS_MANIFEST.yaml).

---

## Quick reference

| Command | What it does |
|---------|--------------|
| `/start-session` | Run L9 sessionStart bootstrap (`make start`) |
| `/ynp` | Highest-leverage next action |
| `/rules` | Load governance rules / project state |
| `/plan` | Execution plan before action |
| `/analyze` | Explore structure, flows, hotspots |
| `/evaluate` | Deep readiness / compliance audit |
| `/analyze_evaluate` | Analyze + evaluate in one pass |
| `/reasoning` | Multi-modal reasoning stack |
| `/gmp` | Phased, auditable execution |
| `/forge` | Fast autonomous batch execution |
| `/harvest` / `/harvest2` | Extract code from docs (sed / copy — no rewrite) |
| `/use-harvest` | Deploy harvested artifacts via plan |
| `/wire` | Governance wiring or component wire-up |
| `/confirm-wiring` | Verify full wiring |
| `/pr` | PR analysis, gaps, merge blockers |
| `/gap-analysis` | Gaps vs target state |
| `/inspect` | External code gate before import |
| `/index` | Export repo indexes |
| `/readme` | README DAG pipeline |
| `/end-session` | Session handoff + memory-bank write |
| `/e2e-blockers` | E2E / local-proof blockers + brief |
| `/mem` | Memory operations |
| `/violation` | Report governance violation |
| `/governance` | Compliance validation |
| `/governance-backup` | Push SSOT to GitHub |
| `/ci` / `/ci-policy` | CI operations / policy |
| `/lint-fix` | Systematic lint fixes |
| `/migrate` / `/refactor` / `/refactor-sweep` | Migration / refactor sweeps |
| `/consolidate` / `/clean_compress` | Cleanup / densify |
| `/extract-chat` / `/extract-from-chat` / `/extract_align` | Chat / pattern extraction |
| `/spec` / `/dag-authoring` / `/update-command` | Spec / DAG / command meta |
| `/probe` / `/audit-component` / `/verify-component` | Component verify ladder |
| `/lcto` | L CTO strategic mode |

---

## Lifecycle

| When | Command |
|------|---------|
| Open / resume a window | `/start-session` |
| Decide what to do | `/ynp` |
| Tracked change | `/gmp` |
| Close the window | `/end-session` |

---

## Activation contract

| Mechanism | Role |
|-----------|------|
| `ops/hooks/session_start_bootstrap.sh` | Auto on Cursor `sessionStart` |
| `/start-session` | Manual — identical bootstrap via `make start` |
| `rules/02-slash-commands.mdc` | Always-on recognition (this table) |
| `commands/COMMANDS_MANIFEST.yaml` | Enabled file map |

If a slash command is missing: run `/start-session` or `make -C "$HOME/.cursor-governance" start WS="$(pwd)"`, then confirm `.cursor-commands/commands/<name>.md` exists.
