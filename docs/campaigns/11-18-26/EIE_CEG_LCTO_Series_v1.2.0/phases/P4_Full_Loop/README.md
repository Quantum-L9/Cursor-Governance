# P4 | Full EIE-CEG feedback, graph-backed scoring and product proof | LCTO execution handoff 1.2.0

**Status:** DRAFT_NOT_ACTIVATED. **Launch:** Explicit activation only. **Campaign ID:** `EIE_CEG_P4_LCTO`.

## Target outcome

Prove the combined product: seeded graph -> CEG gap assessment -> EIE cheap inference/research -> durable graph expansion -> actual CEG scoring/matching and feedback -> next economical enrichment. This is an implementation campaign in a single persistent CTO program: published stacked PRs and green code, not contracts only.

**Observable definition of success:** Final program exit: every P0-P4 stacked PR is published and current-head green, the signed Docker rail is run only after complete publication, Neo4j/scoring/crash recovery proofs pass on pinned composite heads, documents match achieved behavior and remaining findings are explicitly resolved. One signed Gate+EIE+CEG+PostgreSQL+Neo4j test journey verifies actual decision delta, graph richness beyond CRM, no lost facts on restart, domain-neutral second cartridge, and current README/AGENTS/ADR/invariants matching as-built reality.

**Priority zero:** Single-CTO series continuation: no phase restarts or separate operator activation. Require P3 published-green code-ready proof, prepare the signed test rail without executing Docker until G_PUBLISH, and refuse separately green CI as a substitute for G_RAIL; scoring remains default-off unless separately authorized.

## Contract boundaries

- This document is an operator-authorized campaign brief only where the operator's exact scope and approval actually support it. It is not an admitted global semantic source or a runtime proof.
- The current Cursor-Governance LCTO mode, child-prompt renderer and publication authority own execution mechanics. This pack supplies task intent, reservations, evidence and testable gates, not an alternate launcher.
- Agents prepare and maintain their PRs to ready-to-merge; LCTO owns integration and actual merge authority is determined by the current operator/host switch.
- Preserve source truth as OBSERVED / REPORTED / INFERRED / UNKNOWN; no successful workflow can imply unexecuted gate steps ran.

## Scope

**Included:**
- Use existing EIE enrichment-sweep/ledger and CEG health_batch_assess, with caller-provided candidates and EIE-owned research decision.
- Demonstrate actual CEG match or authorized secured score grounded in persisted graph fields/evidence. Remote score remains default-off unless separately authorized.
- Close the return loop through declared CEG graph feedback and EIE next-pass targeting without inventing an external agent coordinator.
- Run signed Gate, EIE, CEG, PostgreSQL and Neo4j in test rail; exact two crash/replay windows; second non-PlasticOS cartridge.
- Update EIE root README, AGENTS, local invariants and current ADR/readme links to reflect the finally verified as-built product, not planned features.
- A single persistent LCTO owns the complete P0-P4 program, integration and final disposition. One operator activation starts the series; later phases are gated continuation in that same session, not new operator approvals.
- Preserve the same reusable CTO coding-agent pool, maximum five concurrent child agents or lower actual host capacity. Run independent disjoint work at once; keep each code writer as sole owner of its branch, affected files and PR remediation.
- Stack every campaign PR on the verified previous campaign PR head within its own GitHub repository. Separate repositories have separate linear trains; bind cross-repository dependencies to pinned commit pairs in the CTO stack ledger.
- Use the current Cursor-Governance governed make pr publication procedure exclusively. Verify the exact PR_BASE and resulting GitHub base/head, refuse ambiguous auto-stack/fallback, never raw push or direct PR creation.
- Each coding agent owns its PR through native fast checks, required existing CI, reviewer comments, fixes and green current-head status. CTO schedules publication, evaluates integration and routes any defects back to the original writer.
- No manual five-service Docker integration or repeated whole-system rail per PR or between phases. After ALL planned PRs in P0-P4 are published and green, test the final composite branch heads once; rerun only affected evidence and the final complete rail if integration defects require corrections.
- Existing Infisical secrets available to Cursor are explicitly authorized for the bounded campaign test/integration need. Use the existing credential bindings, least-privilege scope and no logging/copying/committing secrets; availability is checked at use, not presumed.
- For this campaign only, additional repository-local AGENT.md/AGENTS.md protected-file human-review ceremonies are waived for the declared documentation writer. Global policy, GitHub branch controls, security rules, and actual merge authority are not suspended.

**Excluded:**
- No customer production data, standing enterprise deployment, autonomous CRM writeback or unsafe remote score enablement.
- No new GDS/KGE/forecasting/revenue ops stack, match rank redesign or generalized ontology discovery agent.
- No false claim that unexecuted release/deployment/health tests passed.
- Makefile and Repo.mk in every repository are strictly out of write scope; neither the generated make-v1 facade nor its repository-owned implementation can be edited or regenerated as a workaround.
- No direct edits to Cursor-Governance publication machinery, GitHub .github global semantics, unrelated application modules or deployment/production resources.
- No pre-publication heavy Docker integration runs, no suppression of existing required CI checks, no fake PRs when no code correction is needed.
- No raw git push, ungoverned gh pr create, force-push, arbitrary rebases, permissions bypass or secret leakage.

## Reading order

`00-LCTO-LAUNCH.md` -> `07-RECONCILED-FACTS.md` -> `01-SOURCE-EVIDENCE.md` -> `02-CRITICAL-PATH.md` -> `03-CONCURRENCY.md` -> `lanes/` -> `04-DEFINITION-OF-DONE.md` -> `05-PUBLICATION-SECURITY.md` -> `06-FINDING-REGISTER.md` -> `08-FINAL-RECEIPT.md`.

**No execution claimed by this compiled pack.** The compiler only validated declaration structure, ownership graph and byte integrity. Current authority, actual CI and runtime gates remain execution obligations.
