# P2 | Durable EIE-CEG bidirectional delivery and replay | LCTO execution handoff 1.2.0

**Status:** DRAFT_NOT_ACTIVATED. **Launch:** Explicit activation only. **Campaign ID:** `EIE_CEG_P2_LCTO`.

## Target outcome

Harden accepted EIE->CEG graph synchronization and CEG->EIE inference feedback so an interrupted worker or Gate failure cannot silently lose acknowledged intelligence. This is an implementation campaign in a single persistent CTO program: published stacked PRs and green code, not contracts only.

**Observable definition of success:** Pre-integration phase exit: all in-scope code/docs changes are published in verified per-repository stacked PRs, all required native unit/contract/CI checks are green at exact PR heads, owner remediation complete, and the next phase has compatible contract evidence. Complete Docker/runtime graph proof remains deferred to P4 after all PRs publish. Durable outbound/inbound stores and replay semantics pass negative and restart-injected unit/contract tests with stable idempotency and accepted/applied distinctions; actual process-kill windows, signed replay, and exact Neo4j graph state are P4-only G_RAIL proof.

**Priority zero:** Single-CTO series continuation: no phase restarts or separate operator activation. Confirm process-local pending graph legs and feedback queue semantics against current stores, then reuse EIE PostgreSQL persistence before adding any table/worker.

## Contract boundaries

- This document is an operator-authorized campaign brief only where the operator's exact scope and approval actually support it. It is not an admitted global semantic source or a runtime proof.
- The current Cursor-Governance LCTO mode, child-prompt renderer and publication authority own execution mechanics. This pack supplies task intent, reservations, evidence and testable gates, not an alternate launcher.
- Agents prepare and maintain their PRs to ready-to-merge; LCTO owns integration and actual merge authority is determined by the current operator/host switch.
- Preserve source truth as OBSERVED / REPORTED / INFERRED / UNKNOWN; no successful workflow can imply unexecuted gate steps ran.

## Scope

**Included:**
- Recoverable EIE deferred graph sync using existing SideEffectCoordinator, Postgres models/migrations and pinned payload/idempotency.
- Durable EIE graph inference feedback intake before accepted ACK; no queue-full acceptance or silent drop.
- CEG Gate-only graph feedback emission with explicit tenant/entity/rule lineage, actual authorized trigger and default-off flags respected.
- HubSpot observed association relationship retry/relevance admission and acknowledged-only claims.
- Resolve unsupported score-invalidate path from actual CEG cache/route owner: remove if unused or define an approved route only if necessary.
- Run two real process-restart points and a Gate timeout/replay against Neo4j.
- A single persistent LCTO owns the complete P0-P4 program, integration and final disposition. One operator activation starts the series; later phases are gated continuation in that same session, not new operator approvals.
- Preserve the same reusable CTO coding-agent pool, maximum five concurrent child agents or lower actual host capacity. Run independent disjoint work at once; keep each code writer as sole owner of its branch, affected files and PR remediation.
- Stack every campaign PR on the verified previous campaign PR head within its own GitHub repository. Separate repositories have separate linear trains; bind cross-repository dependencies to pinned commit pairs in the CTO stack ledger.
- Use the current Cursor-Governance governed make pr publication procedure exclusively. Verify the exact PR_BASE and resulting GitHub base/head, refuse ambiguous auto-stack/fallback, never raw push or direct PR creation.
- Each coding agent owns its PR through native fast checks, required existing CI, reviewer comments, fixes and green current-head status. CTO schedules publication, evaluates integration and routes any defects back to the original writer.
- No manual five-service Docker integration or repeated whole-system rail per PR or between phases. After ALL planned PRs in P0-P4 are published and green, test the final composite branch heads once; rerun only affected evidence and the final complete rail if integration defects require corrections.
- Existing Infisical secrets available to Cursor are explicitly authorized for the bounded campaign test/integration need. Use the existing credential bindings, least-privilege scope and no logging/copying/committing secrets; availability is checked at use, not presumed.
- For this campaign only, additional repository-local AGENT.md/AGENTS.md protected-file human-review ceremonies are waived for the declared documentation writer. Global policy, GitHub branch controls, security rules, and actual merge authority are not suspended.

**Excluded:**
- No new Redis stream/message bus/distributed transaction framework or guessed database tables.
- No automatic CEG-triggered paid research or worker permission to invoke operator-only score.
- No production rollout or hidden fail-open ACK.
- Makefile and Repo.mk in every repository are strictly out of write scope; neither the generated make-v1 facade nor its repository-owned implementation can be edited or regenerated as a workaround.
- No direct edits to Cursor-Governance publication machinery, GitHub .github global semantics, unrelated application modules or deployment/production resources.
- No pre-publication heavy Docker integration runs, no suppression of existing required CI checks, no fake PRs when no code correction is needed.
- No raw git push, ungoverned gh pr create, force-push, arbitrary rebases, permissions bypass or secret leakage.

## Reading order

`00-LCTO-LAUNCH.md` -> `07-RECONCILED-FACTS.md` -> `01-SOURCE-EVIDENCE.md` -> `02-CRITICAL-PATH.md` -> `03-CONCURRENCY.md` -> `lanes/` -> `04-DEFINITION-OF-DONE.md` -> `05-PUBLICATION-SECURITY.md` -> `06-FINDING-REGISTER.md` -> `08-FINAL-RECEIPT.md`.

**No execution claimed by this compiled pack.** The compiler only validated declaration structure, ownership graph and byte integrity. Current authority, actual CI and runtime gates remain execution obligations.
