# Single CTO continuity, PR trains and delayed Docker | P3

This phase belongs to **one** operator-activated LCTO series. Do not activate a second CTO or fresh child pool for phase P3. The local 00-LCTO-LAUNCH HOLD is satisfied by the one series activation and its predecessor code-ready gates, not a new human approval. Read the program root 00_SINGLE_CTO_START.md and 01_PR_STACK_AND_COLLISION_PROTOCOL.md. These are task constraints, never a substitute for current LCTO host-rendered child prompts.

## Mandatory execution

- Run disjoint writing tasks concurrently within the current max-five pool; sequentially publish PRs in a **linear train per repository**. GitHub cannot stack a CEG PR onto an EIE PR. Track cross-repo compatible heads in the same CTO ledger.
- Publication is only current governed **make pr** with explicitly verified `PR_BASE`. `PR_STACK=auto` can preserve main on telemetry failure. Reject a publish that lands on unexpected PR base and remediate through the SSOT, without raw git push or direct PR creation.
- An agent owns its PR until review and required CI are current-head green. CTO coordinates and routes remediation; CTO never edits an agent's PR branch.
- No manual Docker / multi-service test **until all P0-P4 campaign PRs are published and green**. Use required native gates and per-PR CI throughout. This phase's early success is code readiness; P4 G_RAIL alone proves integrated runtime.
- Cursor/Infisical existing secrets are authorized for necessary signed **test** integration if present, never expose or invent them, never infer permission to deploy or mutate production.
- Operator waived local **AGENT.md/AGENTS.md** extra protected-document human review for this campaign scope only. No broader security, merge or global-authority waiver.
- **Makefile and Repo.mk are strictly out of scope** across all repositories. Do not edit, regenerate or patch them to resolve CI, stack, publishing or documentation friction.

## Phase P3 exit

Green published PR/fixture-code readiness only; P4 final Docker product proof still pending.
