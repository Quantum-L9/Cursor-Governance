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

Primary slashes match `commands/COMMANDS_MANIFEST.yaml`. Aliases (not primary rows): `/readme` → `/docs`, `/lint-fix` → `/lint`, `/violation` → `/governance`. `/audit-component` is live (`l9-component-verification`). Folded: `/probe`, `/verify-component` remain modes on `/analyze` / `/evaluate` / `/analyze_evaluate`. Retired with no alias: `/rules`, `/git-work-preserve`, `/harvest2`. A consumer overlay `.cursor/commands/{old}.md` still wins resolution order 1st — do not recreate the retired live file.

| Command | What it does |
|---------|--------------|
| `/start-session` | Run L9 sessionStart bootstrap (`make start`) |
| `/autonomy` | Bounded autonomy — parallel Tasks + background PR poll (packet) |
| `/ynp` | Highest-leverage next action |
| `/l9-plan` | Deep PE+autonomy `.plan.md` via first-class template |
| `/l9-plan-simple` | Same template, Cursor Build, then stacked `make pr` (never off `main` if an open PR exists) |
| `/l9-plan-build` | Plan via `/l9-plan-simple`, Improve then Validate & Repair, then Cursor Build under `/gmp` |
| `/l9-audit-plans` | Shelf the plans store: root = current unbuilt; partial/built/superseded/parked in subfolders |
| `/l9-pipeline-audit` | Audit plans + WIP + PE campaigns; harvest via `l9-intelligence-harvest` (`/plan-audit` alias) |
| `/ff` | This Cursor-Governance clone **and** SSOT in parallel (`--clone` / `--ssot` = one target) |
| `/analyze` | Explore structure, flows, hotspots (`l9-code-analysis`; probe mode via `l9-component-verification`) |
| `/evaluate` | Deep readiness / compliance audit |
| `/analyze_evaluate` | Analyze + evaluate in one pass |
| `/audit-component` | Export / wiring / API audit (`l9-component-verification`) |
| `/reasoning` | Structured reasoning (`l9-structured-reasoning`; stance enums, then `/ynp`) |
| `/gmp` | Phased, auditable execution |
| `/forge` | Fast autonomous batch execution |
| `/harvest` | Extract code from docs (sed / copy — no rewrite) |
| `/use-harvest` | Deploy harvested artifacts via plan |
| `/wire` | Governance wiring or component wire-up |
| `/confirm-wiring` | Verify full wiring |
| `/pr` | PR analysis, gaps, merge blockers (Diagnose only) |
| `/pr-train` | Current-branch stacked PRs, halt for remediator Converge, then `--ff-only` when `open_pr=0` |
| `/l9-pr-remediation` | Converge via make pr-check / make pr, then stack-safe oldest-first merge |
| `/gap-analysis` | Gaps vs target state |
| `/gap-analysis-new` | Gap analysis (alternate protocol) |
| `/inspect` | External code gate before import |
| `/index` | Export repo indexes |
| `/docs` | Agent-docs update (`l9-update-agent-docs`; not the README DAG) |
| `/end-session` | Session handoff + Graphiti PICKUP (memory-bank retired) |
| `/e2e-blockers` | E2E / local-proof blockers + brief |
| `/mem` | Memory operations |
| `/governance` | Compliance validation + report-violation mode |
| `/governance-backup` | Push SSOT to GitHub |
| `/ci` / `/ci-policy` | CI operations / policy |
| `/lint` | Systematic lint fixes (no commit) |
| `/migrate` / `/refactor` / `/refactor-sweep` | Migration / refactor sweeps |
| `/consolidate` / `/clean_compress` | Cleanup / densify |
| `/clean` | Cleanup command |
| `/extract-chat` / `/extract-from-chat` / `/extract_align` | Chat / pattern extraction |
| `/spec` / `/dag-authoring` | Spec / DAG lifecycle (incl. thin command binding and CONVERT) |
| `/issues` | Issue remediator (Converge); `/issues diagnose` auditor |
| `/l9-issue-remediation` | Same Converge as `/issues`; chain `/l9-pr-remediation` only at `open_issues=0` |
| `/plan-audit` | Compatibility alias of `/l9-pipeline-audit` |
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
