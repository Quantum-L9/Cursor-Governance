---
name: Compiled pe-loop invariants
compiled: true
overview: "Invariants harvested from mixed donors. Execute via /gmp. Do not make campaign."
todos:
  - id: inv-01
    content: "SC-01: baseline locked: origin/main full SHA recorded at execution start; new branch pe/unified-loop created from that SHA with a clean tree (no foreign files)."
    status: pending
  - id: inv-02
    content: "SC-02: re-land of the 8 unmerged admission/gate fixes (blueprint_ops, accept/collect tools, union-diff verify, L4 named-roots, heredoc-safe matching, memory session-id flags) verified present on the branch with the golden admission loop test passing (main was verified NOT to contain them)."
    status: pending
  - id: inv-03
    content: "SC-03: dispatch integration test passes: render-contract resolves an execution profile and probes a provider and invokes it; the provider result maps to an attempt-receipt pre-submission; worker_cannot_self_verify invariant holds."
    status: pending
  - id: inv-04
    content: "SC-04: record-attempt/verify/evaluate-gate/export-handoff call outcome_publisher and enqueue distill jobs (observable via dry-run queue listing)."
    status: pending
  - id: inv-05
    content: "SC-05: collect_evidence memory-lookup flag returns Graphiti context read-only and fails closed when Graphiti is unreachable (no memory mutation from admission)."
    status: pending
  - id: inv-06
    content: "SC-06: claim emits per-task autonomy_action_id plus packet skeleton via contract_mapper; unit test asserts the mapping without any autonomy-side mutation."
    status: pending
  - id: inv-07
    content: "SC-07: EXECUTION_ROUTING_POLICY extended with codex for tightly-scoped mechanical work; no-match routing returns CAPABILITY_UNSUPPORTED; routing golden vectors pass."
    status: pending
  - id: inv-08
    content: "SC-08: all existing suites stay green: PE conformance (142+), controller (25+), autonomy (56+), compile (5+), campaign-schema (2), plus the shared peer-execution lifecycle test."
    status: pending
  - id: inv-09
    content: "SP-01 Baseline matches locked SHA at execution start (git rev-parse HEAD == 95e4c0088919a3fe53fae36d82c36d69f7c13285)"
    status: pending
  - id: inv-10
    content: "SP-02 merge_gate denies by default and allows only a valid human authorization file (fixture hook runs)"
    status: pending
  - id: inv-11
    content: "SP-03 secrets resolver works from a consumer repo cwd (--check OK)"
    status: pending
  - id: inv-12
    content: "SP-04 authed npm install works via ops/secrets/authed_npm.sh wrapper (npm ci in scratch clone)"
    status: pending
  - id: inv-13
    content: "SP-05 dependency-publish preflight catches unpublished version and fabricated lock integrity (unit fixtures)"
    status: pending
  - id: inv-14
    content: "SP-06 graphiti conflicts filters expired edges (unit fixture)"
    status: pending
  - id: inv-15
    content: "SP-07 policy YAMLs parse and encode the new operating defaults (structural assertions)"
    status: pending
  - id: inv-16
    content: "SP-08 quality gates PASS on changed files (make pr-check)"
    status: pending
  - id: inv-17
    content: "SP-09 no in-flight pe/pipeline-fixes file modified by this program (diff name check)"
    status: pending
  - id: inv-18
    content: "Distill the 9-file PE EIE audit plus Repair Order into one compile_brief-admissible INTENT memo covering at most 30% of the corpus (inference + tenant/Alembic isolation), then emit a validated l9-plan dual artifact that hands that memo to the live PE front door."
    status: pending
  - id: inv-19
    content: "Cursor sessionStart live path (before exit 0) invokes ops/scripts/bootstrap_agent_environment.sh --surface cursor; a test fails if that call edge is removed"
    status: pending
  - id: inv-20
    content: "One machine-readable runtime readiness receipt answers which governance/runtime revisions and state roots a PE invocation will use; UNKNOWN is explicit; unverified mixed revisions fail before PE"
    status: pending
  - id: inv-21
    content: "Phase-lock acquire and governed mutation verify use the same session_id, namespace, workspace, and memory_state_root; mismatch prints both identities"
    status: pending
  - id: inv-22
    content: "pec preflight returns ready/blockers/next_action for draft-admission, reconcile, lease, holder, PREPARED, actor, writable paths, and phase-lock without first failing a controller command"
    status: pending
  - id: inv-23
    content: "draft-contract / compile cannot report success for an artifact the immediate consumer rejects"
    status: pending
  - id: inv-24
    content: "A clean-temp-state integration test reaches EXECUTING and records one schema-valid attempt receipt using real pec.py entrypoints"
    status: pending
  - id: inv-25
    content: "Existing Graphiti and controller safety gates remain enforced"
    status: pending
  - id: inv-26
    content: "After merging #168/#169/#170, finish only the remaining Cursor sessionStart → shared bootstrap → runtime receipt → Graphiti lock identity → PE preflight → producer/consumer → clean-runtime smoke path. Do not recreate bootstrap_agent_environment.sh, Claude install delegation, pre-commit provisioning,"
    status: pending
isProject: false
kind: simple
execute_via: gmp
kernel_pass:
  bound_path: pe_loop_compiled_8-28-26.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-08-28T19:22:00Z
    body_sha256: "e4957adba077a66b5aef5f3bda439ed7f560195319bf4b9520fc52f86a54d269"
    deltas:
      - "Emitted compiled:true / kind:simple / execute_via:gmp from harvest_plan_invariants.py"
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-08-28T19:23:00Z
    body_sha256: "e4957adba077a66b5aef5f3bda439ed7f560195319bf4b9520fc52f86a54d269"
    deltas:
      - "Confirmed no live make campaign heading and Gold Nugget-only harvest"
      - "Stamped kernel_pass after Improve then Validate and Repair"
---

# PLAN: Compiled pe-loop invariants

Harvested without implementation. Gold Nugget kernel cited by path.

## Donors

- `pe_unified_loop_8-20-26.plan.md`
- `pe_pipeline_fix_program_8-20-26.plan.md`
- `pe_eie_scoped_campaign_5469bc8f.plan.md`
- `make-program-execution-start-cleanly-gap-only_8-15-26.plan.md`

## Execute via GMP

Run `/gmp` on this packet. Do not run `make campaign`.
Do not admit a Program Lock. Donors stay on the shelf until they
carry `compiled_into`; this file does not whole-file supersede them.
