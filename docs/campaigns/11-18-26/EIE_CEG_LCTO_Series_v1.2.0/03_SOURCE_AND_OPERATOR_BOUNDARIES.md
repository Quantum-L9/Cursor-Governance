# Source-bound operator decisions and authority separation

Operator scope, 2026-11-18:

1. **One CTO for entire P0-P4**, no new independent CTO per phase. Parallel agents are owned by its current LCTO operating protocol.
2. **All campaign PRs stacked** on verified previous head within each repository. GitHub cannot make a cross-repo branch base. Current Cursor-Governance `resolve_pr_stack.sh` fallback risk is explicitly mitigated by verified parent and actual PR base receipts.
3. **`make pr` is SSOT** for opening and updating PRs. Current EIE Repo.mk already delegates its local `pr` to governance and requires PR_BASE; CEG uses the governance workspace publication route if no verified local equivalent. Never modify Makefile/Repo.mk, bypass validation or publish by raw push.
4. **No whole-system Docker until all PRs have been published and are green.** Unit/contract and existing required CI remain mandatory. Early phase acceptance is code-ready, not graph-proven; P4 G_RAIL is the final actual combined runtime acceptance.
5. **Each coding agent remediates its own PR** to green current-head status. CTO delegates, pins cross-repo heads and integrates; it does not edit their source branches.
6. **Infisical** may supply existing available secrets necessary for bounded test rail; read scope only, no disclosure or production data mutation. Missing permission/material remains a precise blocker.
7. **AGENT.md / AGENTS.md protection suspended** for this campaign's local documentation approval path only. No bypass of actual global law, repository ACL or required CI.
8. **Makefile and Repo.mk out of scope.** Use existing working targets and fix runtime/product defects at their actual owners, not by changing execution facades.
9. **DeepSeek authorized** as a new EIE provider surface for P3 (activation session, 2026-11-18); the AGENTS.md stack claim is updated by the DOC owner in the same wave.
10. **Swarm launch surface:** local subagents of this CTO session (operator decision, 2026-11-18); the cloud `create_session` swarm-role gate does not apply to in-process children — the CTO keeps the fixed-pool, disjoint-lane and transcript-report discipline. The local EIE clone is preserved untouched; lane worktrees branch from fetched `origin/main`.

Source baseline inspected: EIE `29d4eb54942e446a9ac917d2ebe2d9733a4e7aec`, CEG `5d06649ed5587463c11b02594ce26b5ef4ad1733`, Gate `b451b68b98b315f57f0c4f9b99090a437e9dac23`, Cursor-Governance `59c0b3e0fae7418c67b7e3be76c4e3f412ad49dd`, `.github` `00500268eb24de29a5e647a447d6f992d609f6f5`. All are source snapshots, not live activated receipts. At execution rebind current heads, active tenant pack and LCTO projections. No production deployment or merge authority is created by this package.

Current-state rebind (2026-11-18, pack v1.3.0): all five pinned revisions were re-verified equal to the live remote default-branch heads. The local EIE primary clone is diverged — one unpushed local-only commit plus uncommitted edits, five commits behind `origin/main` — so agent worktrees branch from fetched `origin/main` only and the diverged state is preserved untouched. EIE #328 (open, CRM writeback refactor) and dependabot #361-363 are the live collision subjects. The local Cursor-Governance clone is 32 commits behind with a dirty tree: activation rebinds from the current session source, and no lane writes governance. Predecessor evidence: see `06_PREDECESSOR_EVIDENCE_AND_CURRENT_STATE.md`.
