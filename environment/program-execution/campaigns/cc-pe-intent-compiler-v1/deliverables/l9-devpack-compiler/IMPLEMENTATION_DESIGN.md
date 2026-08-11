# Implementation Design — Program Execution Intent Compiler v1

Derived from `CONTRACT_SOURCE.md` (`CC-PE-INTENT-COMPILER-V1`) and ADR-0007…0016.
Build order favors the smallest independently verifiable mutation (contract §10).
Inspect the repo before assuming paths (contract §17); reuse existing modules.

## Pipeline (contract §2)

```
NL goal → program-execution.intent.v1 → Intent Resolver → INTENT_RESOLUTION.yaml
        → Program Synthesizer → Blueprint v2 → official validation → Program Lock → RUN_REQUEST/Controller
```
This is a **compiler boundary**, not a new runtime controller — the existing
Program Execution Controller stays the sole runtime authority (ADR-0010).

## Components

### C1 — `program-execution.intent.v1` schema (§4, Gate A, ADR-0007)
Human-facing entry contract: `objective`, `targets`, `policy_profile`,
`termination`, optional **narrowing-only** `constraints`. Reject fields that
prescribe tasks/files/waves/worker-prompts/test-commands. Add a positive minimal
fixture and a negative "implementation-prescribing input" fixture.

### C2 — `program-execution.intent-resolution.v1` + `INTENT_RESOLUTION.yaml` (§5–§6, Gate B, ADR-0008)
Typed resolution IR. Every material derived requirement traces to
`user | evidence | decision | policy`. Classifier with four classes:
evidence-determined (auto), policy-determined (auto + provenance), reversible
planning choice (auto within envelope), authority-bearing decision (never
inferred → decision or scoped Unknown). Record confidence for target/authority/
repository/intent. Unattributed inference may inform search but never becomes
authority.

### C3 — `quantum-l9.safe-autonomy.v1` policy profile (§7, ADR-0009)
Formalize as `program-execution.autonomy-policy.v1` in the shared/adapter-neutral
governance home (never peer-local, ADR-0013). Owns permission ceilings,
independent-verification requirement, decision auto-resolution classes, Unknown
behavior, bounded-replanning policy, escalation, termination. Overlays may
**narrow, never widen**. Do not duplicate an existing policy system if present.

### C4 — Repository/DPK integration (§8)
Consume existing repo truth when present (`.ai/manifest.yaml`,
`.ai/repository-map.yaml`, `.ai/constraints.yaml`, `.ai/execution-package.yaml`,
`AGENTS.md`, schemas, ADRs, validation/rollback/observability defs, existing DPK
IR). Evidence priority: verified current-state > machine-readable contracts >
repo structure/code > ADR material > human prose > inference. Prefer
`repo → DPK → canonical repo-truth IR → resolver` over a second parser.

### C5 — Program Synthesizer (§9–§12, Gate C, ADR-0010)
Deterministically compile `INTENT_RESOLUTION` → the complete Blueprint v2 source
set required by the **live** `EXECUTION_INDEX.yaml` (do not hard-code the list).
Generate workstreams, tasks, dependencies, waves, evidence requirements,
authorization ceilings, gates, risks, rollback, source traceability. Tasks: one
objective/target, cite authority/decisions/Unknowns/evidence, define
outputs/acceptance/validation/negative-cases/rollback/risk/exact-ceiling/gates;
favor smallest verifiable mutation, no token-driven fragmentation. Acceptance
criteria must be machine-verifiable (command exits zero / schema validates /
negative fixture fails / official validator passes) — never "looks correct".
Emit **design-time definitions only**; never Controller runtime state.

### C6 — Official-validator adapter (§13, Gate D)
Invoke the exact governing Blueprint validator at runtime (`--mode instantiated`);
never maintain a second approximate validator. PASS → eligible for Program Lock;
FAIL → bounded autonomous repair only if it doesn't alter intent, require an
authority decision, or widen a ceiling; otherwise escalate.

### C7 — Program-action resolver (§14)
Decide `create | extend | supersede`. Never silently mutate an immutable Program
Lock; material objective/authority/decision/ceiling/target/convergence changes →
`supersede` with a new lock (ADR-0011).

### C8 — Minimal front-door CLI (§15, Gate E)
`program-execution intent "<goal>" [--target <repo>]`. Emit progress
(parsed → resolved → synthesized → validated → prepared for lock). Ask only for
genuinely unresolved authority-bearing decisions; no questionnaire on the happy
path.

### C9 — Long-chain typed state (§16, ADR-0016)
Persist typed state (original/normalized intent, Program Lock, execution state,
decision/Unknown/evidence/risk registers, attempt/verification/gate receipts,
source traceability). Render fresh minimal per-attempt context; do not replay the
whole conversation. Expose stable interfaces for future `program-execution.replan.v1`.

## Authority rules (§3) — enforce throughout
Precedence: safety/security/legal > latest accepted decision > accepted
architecture/contracts > verified current-state > generated task authority >
implementation > documentation > historical > Unknown (fail closed only where
dependent). Downstream narrows, never widens; generated task scope can't override
architecture/contracts; compiler emits definitions, never runtime state; a worker
claim ≠ verification; authority-affecting defaults need provenance; absent facts
never become authority; Unknowns block only named dependents; permissions never
default to allowed by omission; no remote mutation.

## Test matrix (§18, Gate F) — implement all
happy-path · sparse-input (no needless clarification) · evidence-determined fact ·
policy-determined fact · authority-bearing architecture choice (decision/Unknown,
dependent blocked, unrelated eligible) · missing ownership (no invented owner) ·
Unknown scoping (deployment cred blocks deploy only) · permission widening
(task can't gain push) · structural-vs-runtime evidence (test exists ≠ test PASS)
· conflicting source authority (contract wins) · existing program (supersede, not
silent mutation) · malformed synthesis (bounded repair or explicit blocker) ·
runtime-ownership contamination (rejected).

## Prohibited (§21) & stop conditions (§20)
No commit/push/PR/merge/publish/release/deploy/migrate/destructive/external-
message; no invented owners/credentials/locations/contracts; no weakened
validators or deleted tests; no runtime state in DPK/intent artifacts; no
inference-as-authority. Stop the affected branch (not globally) on unresolved
target, required runtime-authority change, missing accepted architecture
decision, over-ceiling permission need, required remote mutation, validation that
can't pass without weakening governance, or materially stale evidence.

## Independent verification (§23)
After implementation: run deterministic tests, schema validators, official
Blueprint validation, inspect generated fixtures independently of the generator,
and review the final diff for authority widening / undocumented defaults /
runtime-ownership duplication / scope creep / weakened tests / invented
infrastructure / accidental remote capability. Record exact commands and results.
Report implementation + verification state only; do not declare runtime
convergence (§24).
