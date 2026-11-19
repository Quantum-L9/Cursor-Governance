# Predecessor evidence and current state | v1.3.0

This series is the successor of the executed EIE+CEG Flywheel campaign
(`docs/campaigns/11-17-26/CEG-EIE/L9_EIE_CEG_Intelligence_Flywheel_CTO_v1.2.0`,
operator-requested 2026-11-17, code merged 2026-11-13…2026-11-18). Before
assigning any lane, the CTO records the following merged evidence as
already-satisfied where the phases overlap it, and verifies the open items.
"Already satisfied" is recorded as proof; nothing is re-implemented.

## Merged predecessor receipts (verified 2026-11-18 via GitHub API)

| Repo | Merged PRs | What they shipped |
| --- | --- | --- |
| EIE | #347, #348, #349 | integration v2 wiring; plasticos 0.6.0 pack; activation (`domains/plasticos/spec.yaml` now exists at the pin) |
| EIE | #350 | deleted dead `app/health`; aligned docs with ADR-010 |
| EIE | #351 | converge results sync to CEG, detached from the answer |
| EIE | #352 | budgeted enrichment sweep driven by CEG readiness (default-off by design) |
| EIE | #359 | stopped false `score-invalidate` emission and unbound staging ingress (P2 R04 root fix) |
| Gate | #43, #44, #45 | permission/signing work recorded by the Flywheel (entries NOT applied — operator step) |
| CEG | #494, #497, #498 | score/match and feedback paths used by Flywheel lanes B/C |
| Odoo | #506, #507, #512 | plasticos tenant-side work (out of this series' scope) |

## Per-phase effect

- **P0**: docs modernization is PARTIAL — #350 aligned docs with ADR-010 but
  root `README.md` is still absent at the pin, `AGENTS.md` is still 418 lines
  with the 7-row/8-gate table, `docs/INVARIANTS.md` was last reviewed
  2026-04-11, and the dual ADR-011 collision is unresolved. DOC lane work
  stands; it must verify #350's edits, not undo them. ESPEC lane:
  `domains/plasticos/spec.yaml` EXISTS in EIE (plasticos 0.6.0 active via
  #349); CEG has no `domains/plasticos/spec.yaml` at its pin (verified 404).
  The lane verifies compatibility and records proof rather than creating the
  EIE file.
- **P1**: no Flywheel work covered CRM graph seeding — genuinely open.
  SEQUENCING: EIE #328 (open since 2026-11-11) rewrites
  `app/services/crm/{base,hubspot,odoo,salesforce}_client.py` and
  `docs/contracts/*`. The CTO sequences or stacks the CRM lane against #328;
  never rewrite those files concurrently. The series non-goal "automatic CRM
  writeback" matches #328's purpose.
- **P2**: R04 root fix already merged (#359). The OUT lane writes a NEW
  regression file `tests/unit/test_score_invalidation.py` around the merged
  fix. Durable outbox/inbox/replay (R01, R02, R03, R05) remains open work.
- **P3**: inference leverage is partially affected by merged #351; L01-L04
  must be re-verified against current code at activation.
  `app/services/deepseek_client.py` is a NEW provider surface (pinned
  AGENTS.md declares Perplexity only) — the CTO confirms operator
  authorization at G0 before creation.
- **P4**: sweep (#352) and CEG score/match paths (#494/#497/#498) are MERGED
  and default-off by design. SWEEP and DECISION lanes verify and rail-prove;
  they do not re-implement. E2E rail code, DOC and the final G_RAIL remain
  open.

## Open operator-reserved items (do not re-derive in lanes)

1. Gate permission entries recorded by the Flywheel but NOT applied: EIE
   `enrichment-engine-v1` health-assess + sync. Operator applies them; CTO
   verifies at G0/P4.
2. Infisical: the EIE `enrichment-engine-v1` ed25519 keypair creation is
   operator-only. Precondition for P4 G_RAIL signing.
3. EIE #328 disposition (merge or stack) — CTO sequences; merge authority
   remains the operator's.
4. Deployment hold: production deployment is out of campaign scope regardless
   of rail results.

## Environment rebind at activation (2026-11-18 observed)

- All five pinned SHAs were re-verified equal to the remote default-branch
  heads (EIE `29d4eb5`, CEG `5d06649`, Gate `b451b68`, `.github` `00500268`,
  Cursor-Governance `59c0b3e`).
- The local EIE primary clone is DIVERGED: one unpushed local-only commit
  (`5a8c9c1` "docs pass") plus uncommitted edits; five commits behind
  `origin/main`. Every lane worktree branches from fetched `origin/main` at
  the pinned SHA. The unpushed commit and dirty files are preserved, never
  scooped, never built upon.
- The local Cursor-Governance clone is 32 commits behind `origin/main` with a
  dirty tree; lanes never write governance. Activate from the current session
  source and catch the clone up (`/ff`) before any governance-dependent local
  step.
- Open EIE PRs at activation: #328, dependabot #361-363. Open governance PRs
  (#1040-1044, #1036, #1012-1014) are read-only context.

## Recorded operator decisions (activation session, 2026-11-18)

1. **Swarm launch surface:** local subagents of the CTO session on this host.
   The cloud `create_session` swarm-role gate does not apply to in-process
   children; the CTO keeps the fixed-pool (<=5), disjoint-lane and
   transcript-only reporting discipline manually and embeds the rendered
   child-prompt verbatim as each subagent's system prompt content.
2. **Local EIE clone:** preserved untouched (unpushed commit `5a8c9c1` and
   uncommitted edits stay exactly as they are); all lane worktrees branch from
   fetched `origin/main` at the pinned SHA.
3. **Pack storage:** this corrected pack is committed and published to
   Cursor-Governance through the governed `make pr` path as a separate PR;
   open governance PR #1040 occupies a different subdirectory of
   `docs/campaigns/11-18-26/`.
4. **DeepSeek:** authorized as a new EIE provider surface for P3; the DOC
   owner updates the AGENTS.md stack claim in the same wave.
