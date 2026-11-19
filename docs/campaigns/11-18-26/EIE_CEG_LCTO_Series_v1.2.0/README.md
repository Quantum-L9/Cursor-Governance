# EIE + CEG Domain Intelligence Mesh | Single CTO LCTO Campaign Series v1.3.0

**Status:** EXECUTION PACK PREPARED, **NOT ACTIVATED**. **Operator intent:** one persistent CTO and a reusable pool of up to five coding agents; maximize disjoint concurrent implementation with serialized same-repo stacked PR publication. Every actual PR publishes or updates through `make pr`. The operator has authorized existing scoped Infisical secrets for required test integration and waived extra local AGENT/AGENTS human-review protection for this campaign only. `Makefile` and `Repo.mk` are out of scope. Merge and production deploy are not authorized by this pack.

## Start here

Read `00_SINGLE_CTO_START.md` once, then `01_PR_STACK_AND_COLLISION_PROTOCOL.md`. Activate the complete series as one `/lcto` engagement when the operator invokes it. Maintain the same CTO session and child pool across `phases/P0_Domain_Docs` through `phases/P4_Full_Loop`. The individual phase launch briefs are task slices within that single operator-approved campaign, **not separate approval/activation checkpoints**.

| Wave | Source delivery, tested and published green before next wave | Live Docker integration |
| --- | --- | --- |
| **P0** | Native domain/Gate contract corrections and current EIE README, sharp local invariants, AGENTS.md, current ADR index and docs consistency | Deferred |
| **P1** | CRM source fields/entities/associations transformed into typed CEG graph operations and unit/contract proof | Deferred |
| **P2** | Durable EIE-to-CEG outbox and CEG-to-EIE inbox/replay, CEG sender and score invalidation correction | Deferred |
| **P3** | Inference first, strategic unique-unlock mesh, DeepSeek/Perplexity research, provenance and graph-only fields | Deferred |
| **P4** | EIE sweep, CEG score/match, signed Docker test code and final doc PR published and green | **G_PUBLISH then G_RAIL** |

**Critical change relative to v1.0.0:** earlier P0-P3 gates are honest **code-and-PR-ready** milestones rather than prematurely requiring a live signed Docker/Neo4j rail. Once every campaign PR is published and green, one CTO-integrated five-service rail is run against the pinned composite branch heads. Defects go back to their original coding agents' PRs and are retested, not fixed by CTO on someone else's branch.

## Completeness and evidence

This archive preserves the exact original EIE+CEG development pack v1.3.0 and user-supplied template v2.0.0. Every phase includes a compiler-authored `CAMPAIGN.json`, source ledger, exclusive writer lanes, critical path, agent-owned PR/CI remediation and negative-control acceptance. The stack ledger example starts empty; do not report made-up PR numbers, green tests, active LCTO, active Infisical secrets, approved tenant pack or live Docker execution. The provided template compiler validates structural integrity only, not repo correctness or permission.

**Non-goals:** Makefile/Repo.mk mutation, new message broker, parallel CTO sessions, early Docker rail, shadow publisher, automatic CRM writeback, production rollout, unauthorized merge or fake business 10x proof.

## Artifacts

`00_SINGLE_CTO_START.md`, `01_PR_STACK_AND_COLLISION_PROTOCOL.md`, `02_PR_STACK_LEDGER.example.json`, `03_SOURCE_AND_OPERATOR_BOUNDARIES.md`, `phases/` five self-contained source-compiled packs, `reference/` preserved approved technical inputs, and `tools/verify_series.py` verifies authoring hashes and no-collision/phase gates. Original v1.0.0 content is superseded by this pack; application repositories remain unchanged.

## Recursive alignment hardening v1.2.0

The supplied kernel was applied to this exact v1.1.0 ZIP as an audit method. The revised pack includes a source-bound finding/correction report, tightened phase activation, honest P1/P2/P3 code-vs-runtime distinctions, explicit P4 prepublication gates, and executable negative-control tests for ownership and Docker ordering. The EIE v1.3.0 technical development pack and campaign template v2.0.0 remain byte-identical. Read `04_RECURSIVE_ALIGNMENT_AUDIT.yaml` and `05_ALIGNMENT_CORRECTIONS_AND_NEGATIVES.md`. Each phase includes `09-SINGLE-CTO-CONTINUATION.md`; read it before the template-generated phase launch. The native template renderer was validated unchanged. No repo mutation, live PR, CI or Docker is claimed.

## Execution-readiness corrections v1.3.0 (2026-11-18)

- `tools/verify_series.py` and every phase `validate_pack.py` no longer count generated `__pycache__`/`.pyc` entries in the file census: the shipped negative-control suite now passes its positive baseline deterministically (it previously failed because the test module's own import created the cache before the census ran).
- New `06_PREDECESSOR_EVIDENCE_AND_CURRENT_STATE.md`: the executed Flywheel campaign's merged receipts (EIE #347-352/#359, Gate #43-45, CEG #494/#497/#498) are recorded per phase so lanes prove "already satisfied" instead of re-implementing; operator-reserved items (Gate permission application, Infisical ed25519 keypair, EIE #328 disposition) are named.
- Lane corrections: `tests/unit/test_score_invalidation.py` (P2 OUT), `app/services/deepseek_client.py` + `tests/unit/test_enrichment_orchestrator.py` (P3 RESEARCH) and `tests/unit/test_inference_bridge_v2.py` (P3 INFER) are explicitly labeled NEW files; the DeepSeek client is gated on operator authorization at G0 because the pinned AGENTS.md declares Perplexity only.
- Factual corrections: AGENTS.md line count 419 → 418; the stale-docs list narrowed to the two files actually stale at the pin; EIE plasticos 0.6.0 activation (#349) recorded in P0 facts/findings; P2 R04 marked evidence-fixed by merged #359.
- Current-state rebind: all five pinned SHAs re-verified equal to remote default heads (2026-11-18); the local EIE clone carries an unpushed docs-pass commit and dirty files — every lane worktree branches from fetched origin/main; EIE #328 (open) sequences against P1's CRM lane.
- Root `MANIFEST.json` version field aligned (was 1.1.0); the "13 negative-control tests" claim is clarified as the template ZIP's own `tests/test_compiler.py` (the pack's `tools/test_verify_series.py` has 12).
- Governance publication normalization: pre-commit `end-of-file-fixer` added trailing newlines to template-generated files and ruff normalized the two tool scripts at commit; all pack hashes/manifests were regenerated from the normalized bytes, and the kernel provenance pin keeps the original upload digest as `kernel_sha256_original`.
