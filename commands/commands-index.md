---
name: commands-index
version: "3.0.0"
description: "Human index of enabled L9 slash commands (non-skill wrappers only)"
status: active
updated: "2026-08-29"
registry: commands/COMMANDS_MANIFEST.yaml
recognition_rule: rules/02-slash-commands.mdc
---

# L9 Cursor Commands — Index

**Skills are the SSOT.** Thin `commands/*.md` wrappers whose only job was
delegating to one skill pack are **retired** under `commands/_archived/`.
Invoke the skill directly (Cursor plugin / Claude Code `~/.claude/skills/` symlink).

Machine registry: [`COMMANDS_MANIFEST.yaml`](COMMANDS_MANIFEST.yaml) — **18** live
commands (executors, DAGs, bootstrap, or protocols with no 1:1 skill name).

---

## Live slash commands

| Command | What it does |
|---------|--------------|
| `/start-session` | Run L9 sessionStart bootstrap (`make start`) |
| `/gmp` | GMP executor + plan Build (not a skill wrapper) |
| `/governance-backup` | Push governance SSOT to GitHub |
| `/clean` | Workspace cleanup via `make clean` |
| `/harvest` | Harvest deploy DAG (sed/copy path) |
| `/use-harvest` | Deploy harvested artifacts (executor) |
| `/migrate` | Autonomous migration executor |
| `/inspect` | External code gate (inspect DAG) |
| `/refactor` | Refactoring DAG |
| `/refactor-sweep` | Broad refactor sweep protocol |
| `/index` | Export repo indexes (script) |
| `/pr-train` | Stacked PR train DAG → halts for `l9-pr-remediation` |
| `/l9-plan-build` | Plan-simple + kernels + Build DAG |
| `/l9-audit-plans` | Plans-store shelf organizer (not pipeline audit) |
| `/lcto` | L CTO strategic mode |
| `/spec` | Specification generator |
| `/rules` | List governance rules from `.cursor/rules/` |
| `/update-command` | Slash-command minimizer DAG (legacy) |

---

## Invoke skills directly (no `commands/` file)

Examples — full list: `skills/` + `ops/generated/skill-registry.json`.

| Skill | Typical invoke |
|-------|----------------|
| `l9-issue-remediation` | `/l9-issue-remediation` (Claude Code skill slash) |
| `l9-pr-remediation` | `/l9-pr-remediation` |
| `l9-plan` / `l9-plan-simple` | skill name or natural-language plan intent |
| `l9-pipeline-audit` | skill name (`/plan-audit` alias retired) |
| `l9-code-analysis` | analyze / evaluate / extract_align modes in skill |
| `l9-bounded-autonomy` | `/autonomy` retired — invoke skill + packet |
| `l9-ynp` | skill name |
| `l9-repo-sync` | `/ff` retired — invoke skill or `make ff` |
| `l9-end-session` | skill name (force-retry close) |
| `l9-forge` | skill name |
| `l9-ci-ops` | `/ci` and `/ci-policy` retired |
| `l9-graphiti-memory` | `/mem` retired |

Claude Code: every registered skill is symlinked under `~/.claude/skills/` and
`<repo>/.claude/skills/` → `$HOME/.cursor-governance/skills/`. Type
`/skill-name` as a skill slash.

Cursor: skills load via the `l9-governance` plugin; attach or route per
`rules/23-l9-skill-routing.mdc`.

---

## Activation contract

| Mechanism | Role |
|-----------|------|
| `sessionStart` hook | Auto bootstrap |
| `/start-session` / `make start` | Manual bootstrap |
| `.cursor-commands` → SSOT | Command + skill reference plane |
| `l9-governance` plugin | Skill + rule activation |

If a retired slash is typed: resolve the matching **`skills/<name>/SKILL.md`**
from the registry — do not read `commands/_archived/`.
