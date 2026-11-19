# P0 | Domain, Gate seam and EIE documentation modernization | LCTO execution handoff 1.2.0

**Status:** DRAFT_NOT_ACTIVATED. **Launch:** Explicit activation only. **Campaign ID:** `EIE_CEG_P0_LCTO`.

## Target outcome

Modernize EIE README, its local sharp invariants, clean AGENTS.md and current ADR index/decisions, while proving native EIE/CEG domain-pack compatibility and authorized Gate routes for the first end-to-end PlasticOS graph handoff. This is an implementation campaign in a single persistent CTO program: published stacked PRs and green code, not contracts only.

**Observable definition of success:** Pre-integration phase exit: all in-scope code/docs changes are published in verified per-repository stacked PRs, all required native unit/contract/CI checks are green at exact PR heads, owner remediation complete, and the next phase has compatible contract evidence. Complete Docker/runtime graph proof remains deferred to P4 after all PRs publish. EIE root README and AGENTS are current; docs/INVARIANTS.md has enforced, nonduplicative local product invariants; ADRs have a coherent current index/successors; EIE and CEG admit compatible tenant packs and an authorized signed Gate sync path is verified at the specified test level.

**Priority zero:** Single-CTO series continuation: no phase restarts or separate operator activation. Resolve the exact active authoritative PlasticOS CEG domain pack and its schema identity before rewriting any compatibility or graph policy; EIE README/AGENTS/docs can be reconciled independently now.

## Contract boundaries

- This document is an operator-authorized campaign brief only where the operator's exact scope and approval actually support it. It is not an admitted global semantic source or a runtime proof.
- The current Cursor-Governance LCTO mode, child-prompt renderer and publication authority own execution mechanics. This pack supplies task intent, reservations, evidence and testable gates, not an alternate launcher.
- Agents prepare and maintain their PRs to ready-to-merge; LCTO owns integration and actual merge authority is determined by the current operator/host switch.
- Preserve source truth as OBSERVED / REPORTED / INFERRED / UNKNOWN; no successful workflow can imply unexecuted gate steps ran.

## Scope

**Included:**
- Implement new root README.md and clean concise AGENTS.md; update docs/INVARIANTS.md in place, docs/ARCHITECTURE.md, docs/EXECUTION_FLOWS.md, docs/REPO_MAP.md, docs/contracts/README.md and agent index/link references to current code.
- Add 12-15 focused EIE-only domain-neutral product invariants with specific source owner and negative tests; retain stable existing IDs where semantics still apply; do not copy global law into local rules.
- Reconcile historical ADR-010 and both distinct ADR-011 files without rewriting accepted history; create a discoverable current ADR index and successor ADR only for genuinely new/changed decisions.
- Inspect native published EIE and CEG packs; verify typed field/edge/identity/refnamespace compatibility, denied CEG scoring keys in EIE, version pins and Graph sync declarations.
- Prove existing Gate action and caller/worker authorization for signed sync, health-assess, graph-inference-result and sweep route. Repair only observed defects at their actual owner.
- Correct existing EIE docs-consistency check so it refers to real AGENTS.md, docs/INVARIANTS.md and actual eight-gate Repo.mk command; fail on source documentation contradictions without unnecessary CI inflation.
- A single persistent LCTO owns the complete P0-P4 program, integration and final disposition. One operator activation starts the series; later phases are gated continuation in that same session, not new operator approvals.
- Preserve the same reusable CTO coding-agent pool, maximum five concurrent child agents or lower actual host capacity. Run independent disjoint work at once; keep each code writer as sole owner of its branch, affected files and PR remediation.
- Stack every campaign PR on the verified previous campaign PR head within its own GitHub repository. Separate repositories have separate linear trains; bind cross-repository dependencies to pinned commit pairs in the CTO stack ledger.
- Use the current Cursor-Governance governed make pr publication procedure exclusively. Verify the exact PR_BASE and resulting GitHub base/head, refuse ambiguous auto-stack/fallback, never raw push or direct PR creation.
- Each coding agent owns its PR through native fast checks, required existing CI, reviewer comments, fixes and green current-head status. CTO schedules publication, evaluates integration and routes any defects back to the original writer.
- No manual five-service Docker integration or repeated whole-system rail per PR or between phases. After ALL planned PRs in P0-P4 are published and green, test the final composite branch heads once; rerun only affected evidence and the final complete rail if integration defects require corrections.
- Existing Infisical secrets available to Cursor are explicitly authorized for the bounded campaign test/integration need. Use the existing credential bindings, least-privilege scope and no logging/copying/committing secrets; availability is checked at use, not presumed.
- For this campaign only, additional repository-local AGENT.md/AGENTS.md protected-file human-review ceremonies are waived for the declared documentation writer. Global policy, GitHub branch controls, security rules, and actual merge authority are not suspended.

**Excluded:**
- Do not execute P1 CRM import, P2 persistence, P3 provider research, or P4 scoring changes in this phase.
- No CEG or EIE replacement schema manager, no independent L9 invariant admission, and no global constitution edits.
- No raw repository push, automatic merge, production secrets, customer data or deployment.
- Makefile and Repo.mk in every repository are strictly out of write scope; neither the generated make-v1 facade nor its repository-owned implementation can be edited or regenerated as a workaround.
- No direct edits to Cursor-Governance publication machinery, GitHub .github global semantics, unrelated application modules or deployment/production resources.
- No pre-publication heavy Docker integration runs, no suppression of existing required CI checks, no fake PRs when no code correction is needed.
- No raw git push, ungoverned gh pr create, force-push, arbitrary rebases, permissions bypass or secret leakage.

## Reading order

`00-LCTO-LAUNCH.md` -> `07-RECONCILED-FACTS.md` -> `01-SOURCE-EVIDENCE.md` -> `02-CRITICAL-PATH.md` -> `03-CONCURRENCY.md` -> `lanes/` -> `04-DEFINITION-OF-DONE.md` -> `05-PUBLICATION-SECURITY.md` -> `06-FINDING-REGISTER.md` -> `08-FINAL-RECEIPT.md`.

**No execution claimed by this compiled pack.** The compiler only validated declaration structure, ownership graph and byte integrity. Current authority, actual CI and runtime gates remain execution obligations.
