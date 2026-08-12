<!-- --- L9_META ---
l9_schema: 1
artifact_type: wip_learned_lesson
component: program-execution-system-v2
tags: [wip, learned-lesson, ci-gates, preflight, program-execution, phase-0, autonomy, user-config, make-pr, precommit, uv-lock, pins, alignment]
retrieval: on_demand
status: implemented
--- /L9_META --- -->

# Learned Lessons — Program Execution System v2.0.0 (WIP)

> **Status:** LL-001–004 **implemented** in Blueprint/Controller/shared (2026-08-02T22:08:24Z) and promoted to `environment/program-execution/core/`. This file remains the lesson ledger with evidence paths.
>
> **Downstream duty:** Keep acceptance checkboxes and evidence paths current when policies change.

---

## LL-001 — Disable non-true-blocking CI gates before a major PROGRAM

| Field | Value |
|---|---|
| **ID** | `LL-001` |
| **Captured** | `2026-08-02T21:43:21Z` |
| **Source** | Operator test run (CI thrash during program-scale work) |
| **Severity** | High (blocks throughput; false-fail signal) |
| **Implementation status** | `implemented` — 2026-08-02T22:08:24Z |
| **Evidence** | GATE blocking_class + WAIVER program_ci_advisory + RUNBOOK §2 + stop taxonomy + ADVISORY_CI_NOISE |

### Lesson (binding intent)

**Before starting a major Execution Program, disable CI automated blocking gates that are not truly blocking** — for example meta-header requirements and other cosmetic / advisory checks that currently fail-closed in CI but do not protect correctness, security, authority, or merge integrity.

Do this **before** Wave 0 / first mutating wave begins. Do not discover these gates mid-program while leases, digests, and evidence are already in flight.

### Why it matters

- Program-scale work generates many files and docs; meta-header and similar lint-as-block gates create serial false failures.
- False-blocking CI burns tokens, bandwidth, and wall clock without improving program safety.
- Contaminates gate evidence: Controller/Blueprint convergence looks red for reasons outside program DoD.

### In scope (examples of “not truly blocking”)

- Meta / `L9_META` header presence or format requirements when enforced as required CI checks
- Other advisory documentation / labeling / formatting gates that are useful as warnings but should not block program admission, wave promotion, or PR merge during program execution
- Any check classified as cosmetic, style-only, or retrieval-metadata that is currently wired as a hard fail

### Out of scope (remain true-blocking; do not disable)

- Secrets / gitleaks / security scanners that protect real exposure
- Authority, exact-SHA, lease, authorization-ceiling, and evidence-digest gates owned by this pack
- Org invariants, protected-core, and human-merge requirements
- Any gate the program’s `CONVERGENCE_GATES.yaml` marks `blocking: true` for safety/correctness

### Required program preflight (to encode later)

1. Inventory CI checks that can fail a PR / wave admission.
2. Classify each as `true_blocking` vs `advisory_or_cosmetic`.
3. For `advisory_or_cosmetic` that are currently fail-closed: disable, demote to warn, or issue a **scoped, expiring program waiver** *before* program start.
4. Record the classification + waiver IDs in Blueprint evidence; do not leave implicit.
5. Re-enable or leave advisory after program closeout if still desired as hygiene.

### Downstream integration targets (for implementing agent)

Fold into the final pack — do **not** leave this file as the only SSOT once implemented:

| Target | Why |
|---|---|
| `program-execution-blueprint-template/RUNBOOK.md` | New “Pre-program CI gate hygiene” step before Wave 0 |
| `program-execution-blueprint-template/CONVERGENCE_GATES.yaml` (+ schema) | Explicit `blocking` vs advisory classification; forbid treating meta-header-class checks as program-blocking unless justified |
| `program-execution-blueprint-template/WAIVER_REGISTER.yaml` (+ schema) | Pattern for scoped, expiring waivers of non-true-blocking CI gates for program duration |
| `program-execution-controller-template/policy/stop-conditions.yaml` | Stop only on true-blocking failures; do not halt on demoted advisory CI |
| `program-execution-controller-template/references/APPROVALS_WAIVERS_AND_HANDOFF.md` | Document that cosmetic CI disable/waiver is a preflight authority act, not mid-flight improvisation |
| `shared/ERROR_TAXONOMY.yaml` | Distinct error class: `advisory_ci_noise` vs `true_blocking_gate_failure` |
| `environment/program-execution/core/**` (final tree) | Mirror the above once WIP → production promotion runs |

### Acceptance for marking `implemented`

- [ ] RUNBOOK has an explicit pre-program CI classification + disable/waiver step
- [ ] Schemas/policy distinguish true-blocking vs advisory CI gates
- [ ] Waiver path is scoped, expiring, evidence-backed (no implicit omission)
- [ ] True-blocking security/authority gates remain fail-closed
- [ ] Final tree under `environment/program-execution/` reflects the same law (or HANDOFF proves intentional deferral)

### Explicit non-goals

- Do not weaken secrets, org-invariant, or human-merge enforcement.
- Do not permanently delete meta-header tooling — demote or waive for program windows.
- Do not treat this WIP note as runtime authority by itself.

---

## LL-002 — Phase 0 user-config: dial autonomy and stop reasons before long-running execution

| Field | Value |
|---|---|
| **ID** | `LL-002` |
| **Captured** | `2026-08-02T21:45:06Z` |
| **Source** | Operator lesson — long-running autonomous program deployment |
| **Severity** | Critical (false stops abort autonomous runs; under-autonomy is the wrong default for a deployed program) |
| **Implementation status** | `implemented` — 2026-08-02T22:08:24Z |
| **Evidence** | PHASE0_USER_CONFIG.yaml + GATE-000 + program_deploy_max_autonomy + stop_taxonomy + AUTONOMY_BRIDGE.md |
| **Depends on / pairs with** | `LL-001` (CI non-true-blocking gates are one class of stop reason to clear in Phase 0) |

### Lesson (binding intent)

Add an explicit **Phase 0 — user-config** step to the Execution Program lifecycle.

In Phase 0, the operator (or deploying agent under operator authority) **dials in all settings** that can stop, pause, or narrow a long-running autonomous run — not limited to, but **definitely including**:

- autonomy profile / authority ceiling / maturity / lanes
- what is classified as **blocking** vs advisory
- approvals required mid-flight vs pre-authorized for the program window
- push / PR / remediation permissions inside the program envelope
- stop-conditions that are environmental noise vs true business-logic gates
- kill-switch / revoke posture and who may trip it
- any other Controller or IDE flags that can halt admission, scheduling, or mutation

**Goal:** resolve **all possible reasons for stopping** that are *not* actual business-logic decisions **before** enabling longer-running autonomous execution.

**Default when a program is being deployed:** **maximum autonomy** within the declared program authorization ceiling — unless Phase 0 records an explicit, named business decision that narrows it.

True stops that remain after Phase 0 should be:

1. **Business-logic decisions** (required DEC-*, unresolved UNK-* that the program itself declared as blockers), or
2. **Hard safety / integrity** failures (secrets, lease/digest corruption, authority-ceiling widening, org invariants) — never cosmetic CI or unset defaults.

### Why it matters

- Long autonomous runs die on latent config: conservative defaults, undeclared “ask first” gates, advisory CI treated as blocking, missing campaign packet fields.
- Discovering stop reasons mid-flight burns leases, tokens, and evidence continuity.
- A deployed program implies intent to run; timid autonomy defaults fight that intent.
- Operators need one dial-in surface, not ad-hoc edits across `settings.json`, env flags, stop-conditions, and waivers after Wave 0 starts.

### Phase 0 user-config surface (to encode later)

Introduce a first-class artifact, e.g. `PHASE0_USER_CONFIG.yaml` (name may vary), completed **before** Controller admits mutating work:

```yaml
# illustrative — not yet schema-locked
phase: 0
program_deploying: true
autonomy:
  default: maximum_within_ceiling   # default when program is deploying
  profile: REPLACE_OR_ACCEPT_DEFAULT
  authority: REPLACE_OR_ACCEPT_DEFAULT
  autonomous_merge: false           # human merge may remain; mutation autonomy is separate
blocking_inventory:
  true_blocking: []                 # business decisions + hard safety only
  advisory_or_disabled: []          # includes LL-001 class gates
stop_conditions_reviewed: false
approvals_preauthorized: []
open_business_decisions: []         # only these may legitimately halt progress
operator_ack: REPLACE_WITH_NAME_AND_TIMESTAMP
```

Phase 0 is incomplete (fail-closed on program start) until:

- every known stop/pause reason is classified
- non-business stops are disabled, demoted, waived, or pre-authorized
- autonomy is set to **maximum within ceiling** when `program_deploying: true`, unless a named DEC-* narrows it
- remaining blockers are only explicit business decisions (and hard safety)

### In scope

- Autonomy / authority / maturity / parallelism / remediation skill flags
- Stop-condition policy review and demotion of non-business stops
- Blocking vs advisory gate inventory (extends LL-001)
- Campaign / program authorization packet fields that gate mutation
- IDE and Controller env that can force prompts or deny declared program actions
- Pre-authorization of routine approvals that are not business decisions

### Out of scope (still fail-closed)

- Human merge if program policy keeps `autonomous_merge: false`
- Secrets, org invariants, protected-core, exact digest/lease integrity
- Widening past the Blueprint authorization ceiling
- Skipping named business DEC-* / UNK-* blockers declared by the program

### Downstream integration targets (for implementing agent)

| Target | Why |
|---|---|
| New `PHASE0_USER_CONFIG.yaml` (+ schema) in Blueprint template | Dial-in SSOT before waves |
| `program-execution-blueprint-template/RUNBOOK.md` | Phase 0 before authority lock / Wave 0 mutation |
| `program-execution-blueprint-template/EXECUTION_WAVES.yaml` | Formal W0 entry requires Phase 0 complete |
| `program-execution-blueprint-template/INSTANTIATION_GUIDE.md` | Instantiation includes Phase 0 config |
| `program-execution-controller-template/policy/autonomy.yaml` | Deploying-program default = max within ceiling |
| `program-execution-controller-template/policy/stop-conditions.yaml` | Split business-logic stops vs environmental; latter cleared in Phase 0 |
| `program-execution-controller-template/CONTROLLER.yaml` | Reference Phase 0 config / autonomy profile binding |
| `program-execution-controller-template/references/STATE_MACHINE.md` (or equivalent) | No long-run autonomy until Phase 0 ack |
| `shared/AUTHORIZATION_MODEL.yaml` / `ERROR_TAXONOMY.yaml` | `phase0_incomplete`, `non_business_stop_uncleared` |
| `skills/l9-bounded-autonomy` / campaign packet (if Cursor SOP) | Align packet fields with Phase 0 dial-in |
| `environment/program-execution/core/**` | Mirror on promotion |

### Acceptance for marking `implemented`

- [ ] Phase 0 user-config artifact + schema exists and is required before mutating waves
- [ ] RUNBOOK/waves refuse program start when Phase 0 incomplete
- [ ] Deploying-program default autonomy is maximum within ceiling unless DEC-* narrows it
- [ ] Stop-conditions distinguish business-logic vs clearable environmental stops
- [ ] LL-001-class gates appear in the Phase 0 blocking inventory
- [ ] Final `environment/program-execution/` tree reflects the same law (or HANDOFF defers explicitly)

### Explicit non-goals

- Do not equate “maximum autonomy” with autonomous merge or ceiling widening.
- Do not allow Phase 0 to erase required business decisions.
- Do not treat this WIP note as runtime authority by itself.

---

## LL-003 — Prefer local `make pr` (Core-CI mirror) over PR remediation loops

| Field | Value |
|---|---|
| **ID** | `LL-003` |
| **Captured** | `2026-08-02T21:46:49Z` |
| **Source** | Operator lesson — PR remediation cost (time, tokens, patience) |
| **Severity** | Critical (remediation loops are the expensive failure mode) |
| **Implementation status** | `implemented` — 2026-08-02T22:08:24Z (governance law retained; PES now binds it) |
| **Evidence** | GATE-003 + EVID-003 local_pr_gate + DoD + stop local_pr_gate_skipped + evidence policy |
| **Depends on / pairs with** | `LL-001` (clear non-true-blocking CI so local gate matches real blockers), `LL-002` (Phase 0 dial-in must include this gate as mandatory before long autonomy) |

### Lesson (binding intent)

**Only use `make pr`** (alias `make pr-check`) — the local changed-files pre-commit pipeline that mirrors Core CI — as the binding quality gate before opening or updating a PR / admitting program mutation that will hit remote CI.

This should **eliminate or severely reduce** the need for **PR remediation** (CI-fail → agent fix → push → wait → repeat), which consumes a ton of time, tokens/bandwidth, and operator patience.

Governance already states this elsewhere (`AGENTS.md` §6, `CANONICAL_LAW.md` binding pre-PR gate). The gap for this pack: Program Execution must treat “remote CI remediation as the primary quality loop” as a **forbidden / last-resort** path, and treat local `make pr` PASS as a **required preflight / task completion obligation**.

### Why it matters

- Remote remediation is serial, expensive, and context-destroying.
- Local `make pr` is the same class of checks (changed-files pre-commit + ruff + security) without PR round-trips.
- Autonomy campaigns that skip local gate and “fix it on the PR” recreate the exact burn LL-001/LL-002 try to prevent.
- Operator patience is a finite resource; design the program so remediation is exceptional, not normal.

### Already implemented (do not re-invent)

Cite and bind — do not duplicate contradictory pipelines:

| Mechanism | Role |
|---|---|
| `make pr` / `make pr-check` | Changed-files local PR gate (pre-commit + ruff + security) |
| `make pr-security` | Security scanners on changed files only |
| `make precommit` / `make pr-full` | Intentional full-tree / nightly-equivalent — not the default per-PR loop |
| `AGENTS.md` §6 / `CANONICAL_LAW.md` §12 | Fail-closed: do not open/push PR if `make pr` fails |
| Consumer thin Makefile / `l9-ci-core` | Same gate delegated into governed repos |

### Required program behavior (to encode later)

1. Before any task that will open/update a PR or push a branch expected to face Core CI: run `make pr` (or `make -C "$HOME/.cursor-governance" pr WS="$(pwd)"` from consumers) and record PASS evidence.
2. Controller / task DoD: **local gate PASS is required**; remote CI green is confirmation, not the first filter.
3. PR remediation (`l9-pr-remediation`, autonomy poll-fix loops) is **exception path** for residual drift / flaky remote-only checks — not the default quality strategy.
4. Phase 0 (LL-002) must list `make pr` as a mandatory pre-mutation gate and must not authorize “skip local gate, remediate on PR.”
5. Full-tree `make pr-full` / `make precommit` only when intentionally needed — do not confuse with the default changed-files `make pr`.

### In scope

- Blueprint task completion gates / evidence obligations requiring `make pr` output
- Controller stop or non-admission when local gate was skipped before push/PR
- Autonomy / remediation skill routing: remediation only after local gate was already green or for documented remote-only failures
- Handoff receipts that distinguish `local_pr_gate` vs `remote_ci` evidence

### Out of scope

- Replacing Core CI — remote CI remains the independent confirmation
- Weakening scanners to obtain local PASS
- Mandating `make pr-full` on every small change
- Autonomous merge (still human unless separately authorized)

### Downstream integration targets (for implementing agent)

| Target | Why |
|---|---|
| `program-execution-blueprint-template/DEFINITION_OF_DONE.md` | Local `make pr` PASS before “ready for PR/push” |
| `program-execution-blueprint-template/RUNBOOK.md` + Phase 0 / LL-002 config | Mandatory local gate; remediation is exception |
| `program-execution-blueprint-template/TASK_CARDS.yaml` / evidence catalog | Validation obligation: `make pr` evidence ID |
| `program-execution-blueprint-template/CONVERGENCE_GATES.yaml` | Gate: local Core-CI-mirror PASS |
| `program-execution-controller-template/policy/stop-conditions.yaml` | Stop/warn on push/PR without local gate receipt |
| `program-execution-controller-template/policy/evidence.yaml` | Accept `make pr` logs/exit as evidence method |
| `program-execution-controller-template/references/VERIFICATION_AND_RECEIPTS.md` | Local gate before remote remediation |
| `shared/EVIDENCE_MODEL.yaml` / `ERROR_TAXONOMY.yaml` | `local_pr_gate_skipped`, `remediation_without_local_pass` |
| Cross-link `AGENTS.md` / `CANONICAL_LAW.md` | Authority citation — PES adopts, does not fork |
| `environment/program-execution/core/**` | Mirror on promotion |

### Acceptance for marking `implemented`

- [ ] Program DoD / task cards require `make pr` PASS evidence before PR/push admission
- [ ] Controller treats skipped local gate as stop or non-admission (not silent continue)
- [ ] Remediation path documented as exception after local PASS or remote-only failure class
- [ ] Phase 0 / RUNBOOK cites existing governance `make pr` law (no competing pipeline)
- [ ] Final tree reflects the same obligation (or HANDOFF defers explicitly)

### Explicit non-goals

- Do not invent a second local CI stack inside the PES templates.
- Do not ban remediation tools — ban using them as a substitute for local `make pr`.
- Do not treat this WIP note as runtime authority by itself.

---

## LL-004 — Pre-start alignment: uv.lock, pins, and program coherence before mutation

| Field | Value |
|---|---|
| **ID** | `LL-004` |
| **Captured** | `2026-08-02T21:47:55Z` |
| **Source** | Operator lesson — pin/lock drift forces remediation that should never have started |
| **Severity** | Critical (preventable misalignment → mandatory remediation) |
| **Implementation status** | `implemented` — 2026-08-02T22:08:24Z |
| **Evidence** | Phase 0 alignment fields + EVID-004 uv_lock_check + stop lock_or_pin_misalignment + UV_LOCK_DRIFT / TOOLCHAIN_PIN_MISMATCH |
| **Depends on / pairs with** | `LL-002` (Phase 0 dial-in), `LL-003` (`make pr` / lock checks before PR), `LL-001` (don’t let advisory noise mask real pin failures) |

### Lesson (binding intent)

**Before starting** an Execution Program (before Wave 0 mutation / long autonomy), **verify everything aligns** across the program — especially **all `uv.lock` versions and toolchain pins** — so misalignment cannot create a forced remediation loop later.

Do not “start and fix CI.” **Don’t make the mistake to begin with.**

### Why it matters

- Lock/pin drift (`pyproject.toml` vs `uv.lock` vs `requirements.txt` vs pre-commit `rev` vs SDK/core pins) is a classic false-start: work proceeds, then every PR fails the same way.
- Remediation then burns the exact resources LL-003 exists to save.
- Multi-repo programs amplify this: each target can drift independently unless Phase 0 inventories and aligns them up front.

### What “aligns” means (minimum inventory)

Before program start, verify and record evidence for:

| Surface | Check |
|---|---|
| `uv.lock` ↔ `pyproject.toml` | `uv lock --check` / `make uv-lock-check` PASS (or N/A with reason if no lockfile) |
| `requirements.txt` ↔ `pyproject.toml` `[project.optional-dependencies] dev` | Exact pin lockstep per AGENTS.md / toolchain SSOT |
| `.pre-commit-config.yaml` tool `rev`s | Match declared pins (e.g. ruff) |
| l9-ci-sdk vs l9-ci-core pins | SDK wins on conflict; core only for tools SDK omits |
| Per-target repos in the program | Same class of lock/pin coherence on every execution target that will mutate |
| Blueprint / Controller / shared contract versions | Exact major match / declared compatibility |
| Auth, gates, ceilings, DEC/UNK blockers | Program artifacts internally consistent (no contradictory blocking) |
| Local gate | `make pr` (LL-003) after pin alignment, not before fixing locks |

### Required pre-start behavior (to encode later)

1. Phase 0 / Wave 0 entry includes an **alignment checklist** with evidence IDs.
2. Fail-closed: do not admit mutating tasks while `uv lock --check` fails or pin surfaces disagree.
3. Multi-target programs: run the inventory **per target** (or prove shared lock SSOT).
4. Prefer fixing locks/pins in a dedicated alignment task *before* feature waves — never as drive-by remediation mid-feature.
5. Record resolved pin set in evidence so Controllers don’t re-discover drift mid-flight.

### In scope

- Python uv lock + pin SSOT surfaces named above
- Analogous lockfiles when present (e.g. package-lock / pnpm-lock) if a program target uses them
- Cross-artifact program coherence (versions, gates, authority)
- Pre-mutation stop if alignment incomplete

### Out of scope

- Blindly regenerating locks without review (`uv lock` is intentional, not casual)
- Weakening CI lock drift guards to proceed
- Treating “close enough” semver ranges as aligned when the repo policy requires exact pins

### Downstream integration targets (for implementing agent)

| Target | Why |
|---|---|
| `PHASE0_USER_CONFIG.yaml` / Phase 0 schema (LL-002) | Alignment checklist + evidence fields |
| `program-execution-blueprint-template/RUNBOOK.md` | “Align locks/pins before decomposition/mutation” |
| `program-execution-blueprint-template/EXECUTION_WAVES.yaml` | W0 / entry gate: alignment PASS |
| `program-execution-blueprint-template/EVIDENCE_CATALOG.yaml` | Evidence methods: `uv-lock-check`, pin matrix |
| `program-execution-blueprint-template/TASK_CARDS.yaml` | Dedicated alignment task before feature tasks |
| `program-execution-controller-template/policy/stop-conditions.yaml` | `lock_or_pin_misalignment` |
| `program-execution-controller-template/policy/evidence.yaml` | Accept lock-check receipts |
| `shared/ERROR_TAXONOMY.yaml` | `uv_lock_drift`, `toolchain_pin_mismatch`, `program_artifact_misalignment` |
| Cross-link `AGENTS.md` toolchain table + `make uv-lock-check` | Cite existing SSOT; don’t fork pin tables |
| `environment/program-execution/core/**` | Mirror on promotion |

### Acceptance for marking `implemented`

- [ ] Phase 0 / W0 requires lock+pin alignment evidence before mutation
- [ ] Controller stops or refuses admission on lock/pin drift
- [ ] Multi-target programs inventory each mutating target
- [ ] RUNBOOK orders alignment before feature waves
- [ ] Final tree reflects the same law (or HANDOFF defers explicitly)

### Explicit non-goals

- Do not duplicate the AGENTS.md pin table inside every Blueprint.
- Do not auto-commit regenerated locks without operator/program authority.
- Do not treat this WIP note as runtime authority by itself.
