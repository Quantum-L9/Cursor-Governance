# EIE documentation modernization - executable Phase P0 brief

This is a **campaign input**, not a copy of an admitted L9 global law or a live repository edit.

## Source-verified contradictions at EIE 29d4eb54942e446a9ac917d2ebe2d9733a4e7aec

1. Root `README.md` does not exist at this revision (GitHub fetch returned 404). Existing `docs/ARCHITECTURE.md` describes EIE as a CRM field enrichment API; this misses the explicitly intended broader CRM-independent intelligence mesh.
2. Root `AGENTS.md` has 418 lines, begins with `AGENTS.md wins` as asserted law, references an older Perplexity-only model and non-current two-reviewer rules; it says 8 checks but prints a seven-step table. Current `Repo.mk` actually defines eight `agent-check` checks.
3. Active local invariants are `docs/INVARIANTS.md` (not root); date/version 2026-04-11, contains 20 historic `INV-*` rules, obsolete `Every Neo4j query in EIE` phrasing despite EIE not owning a Neo4j driver, incorrect internal links and enforcement claims not independently re-proven.
4. `.github/workflows/docs-consistency.yml` checks missing `AGENT.md` and root `INVARIANTS.md` and `SKIP`s in their absence, so those checks are not real enforcement. It references seven gates instead of eight.
5. Two distinct accepted ADR files both use `ADR-011`: `docs/adr/ADR-011-side-effect-coordinator.md` and `docs/adr/ADR-011-eie-evidence-odoo-mapping.md`. Preserve historical decisions and filenames unless current authority approves a migration; disambiguate with exact path in a current index. The side-effect ADR mentions score-invalidation, which the inspected Gate does not canonically route. Do not silently rewrite history.
6. `docs/CLAUDE.md` (stale 7-gate `agent-check` reference) and `docs/contracts/README.md` (old `CEG[Cognitive Engine Graphs]` node naming) contain contradictions at the pinned revision. `docs/REPO_MAP.md`, `docs/EXECUTION_FLOWS.md`, `docs/FILE_INDEX_FOR_AGENTS.md` and root `CLAUDE.md` were checked at the pin and show no such contradictions there; the stale `kb/` references in REPO_MAP/FILE_INDEX exist only at the local unpushed docs-pass commit, not at the pin. Reconcile material contradictions; avoid blanket cosmetic rewrites.

## Required deliverables within existing owner paths

- `README.md`: root concise orientation: 2D CRM observations -> EIE enrichment -> CEG graph -> CEG scoring/matching -> readiness to EIE -> cost-directed acquisition. Explain *as built* separately from *the phased target*, P0-P4 status, domains and tenant spec ownership, Gate-only transport, startup, limited env/CLI (verified `Repo.mk`), main entry points, test/proof, current flags and links to authoritative docs. Preserve other client domains; PlasticOS is a cartridge, not a code special case.
- `AGENTS.md`: reduce to a clean operational index (target <=150 useful lines when possible) that identifies the upstream `.github` law, current Cursor-Governance LCTO mode and verified repo-local code/ABI as owners. Include repo boundary matrix, active runtime paths, exact repo `Repo.mk` gates, mandatory source recheck, ADR/spec rules, how to avoid colliding changes, `make pr` verified procedure, and forbidden false completion/unsafe writes. Do not copy a CTO system prompt, weakened security policy, or speculative command. Preserve actual required obligations by linking owner rather than deleting them.
- `docs/INVARIANTS.md`: update IN PLACE. Preserve existing `INV-*` identifiers where still applicable; correctly deprecate or supersede proved obsolete statements with source-backed links. Add a small product-local `EIE-INV-*` section with concrete proofs below, not another global invariant registry. Classify enforcement OBSERVED / PARTIAL / NOT_ENFORCED and attach tests rather than label all COVERED.
- `docs/adr/`: add a terse current `INDEX.md` with ID, filename, status, last verified source, superseded_by, actual owner. Preserve ADR-001..012 history including the two ADR-011 filenames; add a successor product-architecture/graph-handoff ADR only if decision not already owned by a current ADR. Never replace an accepted ADR with a contradictory reinterpretation. Preserve waiver references to ADR-001..007.
- `docs/ARCHITECTURE.md`, `docs/EXECUTION_FLOWS.md`, `docs/REPO_MAP.md`, `docs/contracts/README.md`, `docs/FILE_INDEX_FOR_AGENTS.md` and narrowly referenced provider-specific agent guidance: update entrypoints, CEG/Gate transport, no direct graph driver, source-of-truth field mapping, internal vs external v2 response graph facts, and actual deferred delivery semantics with future limitations explicit. Do not claim P1-P4 built in P0.
- Existing `.github/workflows/docs-consistency.yml` and local docs-guard scripts: point at actual files and status, ensure failing negative fixtures for absent docs or contradictory gate count. Add no new CI framework or extra job if existing gate can enforce.

## Compact local EIE product invariant candidates (refine against code; avoid duplicates)

| ID | Mechanically falsifiable behavior | Primary enforcement seam |
|---|---|---|
| EIE-INV-01 | No generic engine branch chooses a PlasticOS field, ontology edge or commercial threshold; tenant spec supplies names/rules. | Native spec/loader and generic-rule tests |
| EIE-INV-02 | Missing CRM column does not exclude a domain-declared valid graph-enrichment target; client response/writeback may remain narrower. | Convergence vs internal graph projection test |
| EIE-INV-03 | EIE does not hold a Neo4j graph driver or write CEG nodes directly; authenticated Gate `sync` is the only active graph-write ingress from EIE. | Import boundary / packet router test |
| EIE-INV-04 | Typed CEG sync honors tenant, subject, node/property declaration and version pin; undeclared or wrong-typed values never become graph facts. | Spec compatibility and CEG row/edge ingress tests |
| EIE-INV-05 | Deterministic inference closure runs before first paid query whenever derivations are available; no-call route wins when sufficient. | Rule-only zero-provider-call test |
| EIE-INV-06 | A candidate acquisition ranks unique reachable downstream values, not duplicate rule paths or guessed economic coefficients; no paid request without defensible marginal benefit. | Multi-hop, reconvergence and no-value negative fixtures |
| EIE-INV-07 | External claims requiring web evidence must link their field to returned retrieval evidence; fabricated URLs or prompt-only citations do not count. | Per-provider field evidence test |
| EIE-INV-08 | Observed source membership, model claim and deterministic rule inference retain distinct statuses and lineage; inferred requires versioned actual rule. | v2 evidence and CEG observed-edge rejection tests |
| EIE-INV-09 | `completed` may attest EIE's durable convergence result, never silently imply CEG graph ACK; pending graph leg remains recoverable across restart. | SideEffectCoordinator kill-before-ACK fixture |
| EIE-INV-10 | `graph-inference-result` accepted by EIE is recoverable after restart or explicitly refused; process-local queue fullness cannot silently drop accepted data. | GraphReturnChannel queue saturation/replay test |
| EIE-INV-11 | Repeated operation/candidate/edge with the same tenant and evidence identity is idempotent; a different tenant never shares graph identity or acceptance. | Duplicate signed packets and tenant split test |
| EIE-INV-12 | CEG decides matching/ranking/scoring and source relevance admission; EIE cannot forge scoring semantics, actor permissions or source `observed` evidence. | Native spec excludes CEG keys / scored evidence test |
| EIE-INV-13 | CEG readiness may prioritize new knowledge but EIE alone authorizes paid research within current budget, observed cost and deadlines; unavailable CEG cannot become fake readiness. | Sweep disabled/timeout/cost/negative test |
| EIE-INV-14 | A successful EIE request, Gate ACK, or independent CI never proves graph readback, source attribution or improved CEG decision until those outcomes are actually observed. | Cross-engine integration receipt negative control |

**Critical implementation note:** A local invariant is only adopted after checking whether a current `.github` global invariant or existing local contract already governs it. Add a test at the earliest owner where a distinctive regression can be falsified; a prose-only new section does not close this work. Do not promote these candidate IDs as globally admitted by putting them in a README.

## ADR integrity / supersession test

Retain historical ADR-010 as the ownership boundary: EIE evidence/inference versus CEG matching/scoring. ADR-011-side-effect-coordinator remains historically accepted but may require a new successor for durable recovery, not an after-the-fact edit implying it already existed. Evidence-Odoo mapping ADR-011 independently names consumer review/proposal-only semantics and must remain distinct. If a new product/graph handoff ADR is needed, bind current exact source and a new unused identifier after enumerating the directory. Ensure conflict-free index, links and source/test references, not renumbering without provenance.

## Docs exit proof

A phase-0 docs reviewer should be able to start at README, locate AGENTS, INV docs, ADR index and live source owners, and verify `make agent-check` and governed `make pr PR_BASE=...` exactly against Repo.mk. Existing docs-consistency job MUST fail a negative fixture with mismatched path/count/authority, not skip. No PlasticOS hardcoding is introduced by docs-driven code fixes.
