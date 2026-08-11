<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/gemini/README.md
layer: adapter
owner: governance-control-plane
status: active
version: 1.1.0
updated: 2026-07-31
/L9_META -->

# Gemini Adapter — L9 reviewer node on Gemini CLI

Registry identity: `agents.gemini` (`agent_id=gemini`, `user_id=gemini_agent`,
role `reviewer`, **active**). Contract: `../ADAPTER_CONTRACT.md`.

As a reviewer, Gemini writes ONLY into `<group>.reviews` namespaces of its
assigned repos — the server rejects anything else once principals are rendered.

| Need | Carrier |
|---|---|
| Skill discovery | git-tracked `GEMINI.md` / context files |
| Boot context | `gemini-block.md` in `GEMINI.md` |
| Shared memory | `settings.template.json` → `~/.gemini/settings.json` + env |
| Operator steps | **`setup.md`** |
| Autonomy surface | Cite `ops/autonomy/surface_profile.yaml`; set `L9_GOVERNANCE_SURFACE=gemini` |

## Autonomy

Mount the shared Autonomy Surface Profile (CANONICAL_LAW §6.1 / ADAPTER_CONTRACT).
Standing A4 when enabled; human merge only. Do not fork Profile prose.

## Setup

1. Live memory + gemini token on C1 (`docs/DEPLOY.md`).
2. Export `environment.env.example` in the shell that launches Gemini.
3. Merge `settings.template.json` into `~/.gemini/settings.json`.
4. Add `gemini-block.md` to governed repos' `GEMINI.md`.

## Role limits (reviewer)

Review episodes only (`<group>.reviews`): PR findings, CI triage, quality
audits. No implementation claims, no promotion. Claims follow
`WORK_CLAIM_PROTOCOL.md` with task titles prefixed `review:`.
