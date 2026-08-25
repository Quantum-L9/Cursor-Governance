---
name: Kernel compile ADRs
overview: Amend plan.pe.kernel-bind.v1 with two Cursor-Governance ADRs that lock “kernels compile, they do not run” and the worker context cap as constellation law—so context is reserved for the work, not the cookbook.
todos:
  - id: amend-plan-json
    content: Add T08, ADR success criterion, scope.in paths, doc surface, and gmp may_modify to pe_kernel_bind.plan.json; re-validate
    status: pending
  - id: amend-plan-md
    content: Mirror T08 + ADR-0023/0024 locked decisions into pe_kernel_bind_564db18b.plan.md Execute/DAG/handoff
    status: pending
  - id: write-adr-0023
    content: "At execute: canonical ADR-0023 kernels-compile-they-do-not-run + docs/decisions pointer (re-probe number)"
    status: pending
  - id: write-adr-0024
    content: "At execute: canonical ADR-0024 worker-context-is-the-ticket + docs/decisions pointer; cite ADR-0010"
    status: pending
  - id: bind-adapter-and-brief
    content: "At execute: adapter cites both ADRs; worker-brief lint forbids kernel filenames"
    status: pending
isProject: false
---

# Add constellation ADRs to the kernel-bind plan

Amend [pe_kernel_bind.plan.json](/Users/macm2/.cursor/plans/pe_kernel_bind.plan.json) and [pe_kernel_bind_564db18b.plan.md](/Users/macm2/.cursor/plans/pe_kernel_bind_564db18b.plan.md). Do not start a second campaign. ADRs land in the same Cursor-Governance factory PR as the bind.

Parent plan stays: kernels project onto PE objects; PE refuses stubs; no new runner stage; no l9-ci-core product writes; no dirty `~/.cursor-governance` primary.

## Why ADRs (not more kernel prose)

ADR-0010 already treats **rule** activation as compiled and context-budgeted. PE task runtime has no equivalent: nothing forbids a worker from opening CHANGE.md (1,673 lines) and burning the window. That must be org law, not a chat preference.

`always` / important-looking doctrine is not a reason to load kernels. Context is reserved for the leased ticket.

## Home and numbering

User lock: Cursor-Governance `docs/decisions/`.

Follow the 0017–0022 execution series (do not fork a second full body):

- Canonical: [`environment/contracts/execution/adr/`](/Users/macm2/.l9/gov-worktrees/pe-context7-stack/environment/contracts/execution/adr/) `ADR-0023-…` and `ADR-0024-…`
- Catalog pointer only: [`docs/decisions/`](/Users/macm2/.l9/gov-worktrees/pe-context7-stack/docs/decisions/) same filenames, same shape as [ADR-0022 pointer](/Users/macm2/.l9/gov-worktrees/pe-context7-stack/docs/decisions/ADR-0022-thin-adapter-conformance-is-merge-blocking.md)

Re-probe the next free number at execute (today the series ends at **0022**). If 0023/0024 are taken, take the next two free IDs. Do not reuse the overlapping 0010–0014 rule-series numbers.

Format: Status, Date, Context, Options (≥2), Decision, Consequences. One to two pages. Present tense. Skill: `l9-architecture-decision-records`.

## ADR-0023 — Kernels compile; they do not run

**Decision:** Control-plane kernels are compile-time law. They are not runtime prompts and not a second executor.

Must include:

- Kernels (AUDIT / PLAN / BUILD / CHANGE / VALIDATION / DoD / RELEASE) compile into PE machines: adapter YAML, schema fields, refuse-stub compile, pec `kernel_verdict`, DoD gates, Diagnose First predicates.
- Workers, skills, and AGENTS.md MUST NOT instruct “read the seven kernels then execute.”
- `kernel_profile` is an enum on the contract (`BUILD|CHANGE|AUDIT`), not an attached markdown pack.
- Validate & Repair / Recursive Leverage / Improve are not loadable profiles.
- Applies constellation-wide: every Quantum-L9 `make campaign` and every kernel pack consume path. No “just this once” exception.
- When PE extracts to its own repo later, this ADR moves with `environment/program-execution/`; kernel doctrine stays SSOT; the adapter remains the ABI.

**Rejected:** Load kernels at task time (context death + hallucination). Documentation-only enforcement (already failed; same as ADR-0022). A kernel CLI / eighth Core workflow / new `UNTIL_STAGE`.

**Cite:** ADR-0010 (compiled activation + budget), ADR-0022 (prose-only doctrine drifts).

## ADR-0024 — Worker context is the ticket, not the cookbook

**Decision:** After arm, the only worker prompt is the Rendered Contract + `WORKER_BRIEF.md`. Context is reserved for the work.

Must include:

- Hard cap: brief + closed contract JSON + `kernel_profile` one-liner + (CHANGE only) Diagnose First booleans **already evaluated by code** + one nugget claim sentence. Not the extractor essay. Not the operator memo (`load_operator_brief: false` stays).
- LLM sockets: (1) PLAN window before seal — writes fields then exits; refuse if it cannot fill. (2) Leased task worker — mutate declared paths only. Verify, CHANGE dispatch, and DoD are code.
- Extends ADR-0010 from generated **rules** to PE **task runtime**. Same scarce-`always` spirit: kernel markdown is never `alwaysApply` into a worker.
- A test or lint that greps worker brief / launch `next` for kernel filenames (`CHANGE.md`, `VALIDATION.md`, …) is merge-blocking for this bind.

**Rejected:** Re-open the operator brief after arm. Dump kernel excerpts into `WORKER_BRIEF.md`. Seven-pass Improve / ceremonial pass counts.

## Parent-plan edits (same PR, early on the DAG)

Insert **T08** after T00, before T01 (law before adapter):

- Write ADR-0023 + ADR-0024 canonical bodies + `docs/decisions/` pointers.
- Adapter [`ai-control-plane.project-policy.yaml`](/Users/macm2/.cursor/plans/pe_kernel_bind.plan.json) MUST cite both ADR ids.
- `WORKER_BRIEF.md` renderer in [`contracts.py`](/Users/macm2/.l9/gov-worktrees/pe-context7-stack/environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py) MUST NOT append kernel paths (T06/T07 prove this).

Add success criterion: both ADRs Accepted in-repo; worker-brief contains no kernel filenames; `project-policy.yaml` references ADR-0023 and ADR-0024.

Add to `scope.in`: the four ADR paths. Add to `doc_root_surface_impact`: `docs/decisions/` + `environment/contracts/execution/adr/`. Add to `gmp_handoff.may_modify`. Keep l9-ci-core kernel doctrine files in `must_not_modify` (no pointer ADR there — user lock).

Critical path becomes: T00 → **T08** → T01 → T02 → …

## Out

- No ADR in l9-ci-core.
- No rewrite of the seven kernel doctrine files.
- No org-pack / Quantum-L9/.github copy in this PR (Cursor-Governance is the catalog; consumers follow it).
- Do not implement code in this amendment step beyond updating the two plan artifacts when the user authorizes execute.
