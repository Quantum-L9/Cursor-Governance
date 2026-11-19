# Recursive alignment corrections and negative controls | v1.2.0

This is the correction record for the verified v1.1.0 target ZIP. The uploaded `recursive_architecture_alignment_auditor` v1.0 kernel is an **audit method**, not canonical L9 authority, an authorizing grant, or a source of EIE domain meaning. The operator specifically authorized **editing and repackaging campaign artifacts**, not repository code mutation or production release. Audit targets include the 128 files in the predecessor ZIP plus their embedded template and technical-development references. Embedded ZIPs are preserved byte-for-byte and treated as supporting inputs, not independently proven deployed code.

## Root-cause findings, disposition and executable closure

| Finding | Severity / confidence | Governing rule | Predecessor evidence | Correction applied to this pack | Proof |
| --- | --- | --- | --- | --- | --- |
| RA-01 | High / Confirmed | Operator no collision; kernel ownership-and-validation | `tools/verify_series.py` said 'exclusive ownership' without checking whether writers' write paths overlap; it checked only exact Makefile names | Stronger verified lane path ownership, wildcard overlap, repo access, forbidden write surfaces and gate dependency validator | Known-bad colliding writer and forbidden `Makefile` witness rejected; unchanged good fixture passes |
| RA-02 | High / Confirmed | One-CTO operator decision; audit intent/authority | All five phase launch briefs said `HOLD until explicit operator activation`, despite single parent CTO | Each phase gets explicit `09-SINGLE-CTO-CONTINUATION.md` showing inherited series activation and predecessor gate; preserve native generated phase launch byte-for-byte | Companion continuation presence and source binding checker; missing or false independent activation text rejected |
| RA-03 | High / Confirmed | User Docker-after-publication barrier; audit validation truth | P1 observable done implied live Neo4j readback, P2 crash-survival wording implied real process kill, P3 wording claimed persistent CEG data, while full rail was P4-only | P1/P2/P3 source and README now restrict early proof to fixtures/store injection/typed schema; real readback/crash/signing deferred to P4 | Source/README claims checked, no early G_RAIL; final runtime remains NOT RUN |
| RA-04 | High / Confirmed | User Docker-after-publication and all PRs green | P4 G_PUBLISH required DOC and E2E PRs in prose, but did not express either as a prerequisite gate | New G_E2E_CODE and G_DOC_PREP gates, both prepublication, both parents of G_PUBLISH. G_DOC remains post-G_RAIL factual reconciliation | Gate DAG and prepublication negative check |
| RA-05 | Medium / Confirmed | Contract/readability consistency | P4 priority zero read 'require P3 complete and a signed three-service test rail' before G_PUBLISH | Signed rail is now **prepared** prepublication and **executed** after G_PUBLISH only | P4 source and critical path agree |
| RA-06 | Medium / Confirmed | Kernel source-of-truth & exact-target | v1.1 pack relied on a validator with limited checks and had no kernel-specific audit trace | Added revision-bound YAML audit, exact kernel SHA source, correction ledger, validation tests | ZIP CRC, full phase digests, source SHA, negative controls |
| RA-07 | Medium / Unknown-runtime | L9 owner / user current controls | Infisical access, domain-pack admission, full Gate signing, merged head state and Neo4j readiness are not observable from an archived campaign | Keep these as **execution-stage Unknowns** with exact recheck points, not false-green evidence | Only running CTO resolves at activation and P4 G_PUBLISH/G_RAIL |

## Cross-engine boundary matrix retained, not reinterpreted

- EIE: CRM reads and typed domain mapping; inference and provider acquisition; evidence and durable inbound/outbound state.
- CEG: tenant-bound Neo4j node/edge materialization, graph readiness, scoring and matching; graph-origin feedback.
- Gate: authorized signed transport and caller-policy enforcement, not a graph writer or schema authority.
- Tenant-approved EIE and CEG native specs: distinct native schemas and hashes with verified compatibility at required typed boundaries. No PlasticOS rules added to generic engine code.
- Cursor-Governance: opt-in current LCTO mode, real rendered child prompts, `make pr` publication and PR overlap policy; **not** copied into new pack-level implementation authority.

## Campaign runtime proof order, after **one** operator activation

1. Rebind exact code/projections and establish parent session and identity; docs work can begin while published domain pack provenance is resolved.
2. Continue P0 through P4 with one CTO and <=5 reusable workers; per-repository exclusive write sets, stable branch ownership, actual agent-owned PR green/remediation. No Makefile/Repo.mk edits.
3. Per-repository PR stack uses verified explicit parent and governed `make pr` only. A live change of parent invalidates dependent child code-ready proof, not unrelated repositories.
4. P4 G_E2E_CODE and G_DOC_PREP are fulfilled as **authored/published/green** before G_PUBLISH, without invoking Docker.
5. Only after all PRs are current-head green, final composite SHAs pinned and scoped test secrets available: execute the signed Gate/EIE/CEG/PostgreSQL/Neo4j G_RAIL.
6. On actual rail defects, agent owner remediates their own PR, republish via `make pr`, invalidate affected downstream proof, and rerun the terminal rail on updated heads.
7. G_DOC checks final *observed* state. Merge/deploy remain separate authorized decisions.

## Negative controls to run on the package (not the product)

Run `python3 tools/test_verify_series.py`; it must demonstrate that a fabricated same-repo collision is rejected, wildcard docs overlap is rejected, Makefile/Repo.mk are denied, a missing E2E/DOC parent on G_PUBLISH is denied, a prepublication Docker rail edge is denied, and a separate-phase operator-activation instruction is denied. Positive baseline must pass. These prove **pack guardrails**, not running GitHub CI or a live Neo4j graph.

## Explicit residual Unknowns

- Real approved PlasticOS tenant pack (EIE and CEG), current revision and production-admission state: Unknown until current owner resolution at P0/P4.
- Actual signing keys, caller policies and Infisical permissions in selected test environment: Unknown until CTO test binding at P4.
- All future branch/PR/CI/host-mode results: Unknown until generated by current host/GitHub.
- Any local repo authorization/projection drift after pinned source revisions: re-resolve at activation. Do not change .github canonical law or clone its invariants.
- Signed Docker proof, graph readback, actual before/after scoring and two process kills: NOT RUN by pack authoring.

## v1.3.0 execution-readiness corrections (2026-11-18)

| Finding | Severity / confidence | Root cause | Correction applied to this pack | Proof |
| --- | --- | --- | --- | --- | --- |
| RA-08 | High / Confirmed | Validator self-pollution | `file_inventory` and every phase `validate_pack.py` census now exclude `__pycache__` dirs and `.pyc` files, so the shipped negative-control suite's positive baseline passes deterministically (before: the test module's own import created the cache before the census ran, failing the pack's own positive control). | `tools/test_verify_series.py` 12/12 including `test_positive_full_artifact` |
| RA-09 | High / Confirmed | Missing predecessor evidence | New `06_PREDECESSOR_EVIDENCE_AND_CURRENT_STATE.md` records the executed Flywheel campaign's merged receipts (EIE #347-352/#359, Gate #43-45, CEG #494/#497/#498) and per-phase already-satisfied mapping; SERIES.json names the predecessor. | 06 doc + SERIES `predecessor_evidence` |
| RA-10 | High / Confirmed | New files unlabeled; new provider surface | P2 OUT `test_score_invalidation.py`, P3 RESEARCH `deepseek_client.py` + `test_enrichment_orchestrator.py`, P3 INFER `test_inference_bridge_v2.py` are labeled NEW in lane briefs; the DeepSeek client is gated on operator authorization at G0 (pinned AGENTS.md declares Perplexity only). | Lane md corrections + P3 RESEARCH acceptance |
| RA-11 | Medium / Confirmed | Factual drift | AGENTS.md 419 → 418 lines; stale-docs list narrowed to the two files actually stale at the pin; EIE plasticos 0.6.0 activation (#349) recorded; P2 R04 marked evidence-fixed by merged #359; template-compiler "13 tests" claim clarified as the template ZIP's own `tests/test_compiler.py`. | reference/01 + P0 copy + P0/P1/P2/P3/P4 CAMPAIGN.json |
| RA-12 | Medium / Confirmed | Environment rebind | All five pinned SHAs re-verified equal to remote default heads; local EIE clone divergence and unpushed commit documented as a hard worktree-origin rule; EIE #328 sequencing recorded in P1 CRM lane exclusions. | 01/03/06 docs + P1 CAMPAIGN.json |
| RA-13 | Medium / Confirmed | Governance pre-commit EOF/ruff normalization on first publication | Trailing newlines added by `end-of-file-fixer` and ruff formatting applied to pack scripts at commit; manifests/hashes regenerated from normalized bytes; kernel upload digest preserved as `kernel_sha256_original`. | pre-commit green on pack paths + all pack validators PASS |
