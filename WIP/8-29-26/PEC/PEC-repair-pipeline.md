# Program Execution repair pipeline — remaining work

**Updated:** 2026-08-31 — W0–W7 landed at `e8785018`; re-verified at baseline `450b7d0e`.
Two external microscope audits reconciled (see **External audit reconciliation**): **W4 and W5
are contract-delivered but not end-to-end closed**, and a previously untracked Blueprint→execution
seam carries three P0s. Next = **W8**, with the reopened residuals below folded in.
**Machine SSOT:** [`PEC-repair-pipeline.json`](./PEC-repair-pipeline.json)
**Cursor Build plan (W0–W7 done):** [`docs/plans/pec-repair-pipeline-w0-w10_056a9b48.plan.md`](../../../docs/plans/pec-repair-pipeline-w0-w10_056a9b48.plan.md)
**PLAN_DOCUMENT (W8-forward):** [`PLAN_DOCUMENT.pec-repair-pipeline.v1.json`](./PLAN_DOCUMENT.pec-repair-pipeline.v1.json)
**Sources:** moved to [`_archive/`](./_archive) and deprecated. Do not execute from archived files.
**Live SSOT is this trio** — this file (narrative), `PEC-repair-pipeline.json` (machine),
`PLAN_DOCUMENT.pec-repair-pipeline.v1.json` (W8-forward plan). Ignore `_archive/DEPRECATED.md`'s
claim that the `.md` / `.json` "are gone" — see *Already done*.

This folder is no longer a dump of PE research. It is one remaining pipeline.

---

## What this is

PEC already has a strong runtime (Program Lock, authorization, evidence, replan contract, peer execution, `refuse_publication`). W0–W7 closed the compiler front half through shadow graduation.

**Do not build RiskPacket next. Do not `make campaign` next.**

W8+ requires a **new plan** bound to a fresh `origin/main` SHA after W7 merges.

---

## Order (do not reorder)

| Wave | Contract | Status | Depends on |
| --- | --- | --- | --- |
| **W0** | `PEC-WORKER-DIAG-001` | **Complete** | — |
| **W1** | `BOOTSTRAP-PEC-000` | **Complete** | W0 |
| **W2** | C0 | **Complete** | W1 |
| **W3** | C1 | **Complete** (execute residual) | W2 |
| **W4** | C2 | **Complete (contract)** — residual A3 reopened | W3 |
| **W5** | C3 | **Complete (contract)** — residual A4 reopened | W4 |
| **W6** | C4 | **Complete** | W5 |
| **W7** | C5 | **Complete** (shadow only) | W0 + W6 |
| **W8** | PE v3 S0–S8 + C6 | **Open** | W7 |
| **W9** | C7–C10 | **Open** | W8 |
| **W10** | C11 | **Open** | W9 |

W8+ is forbidden until a separate plan with a fresh baseline SHA.

---

## Verified at HEAD (`35880e70`)

| Check | Evidence |
| --- | --- |
| W0 worker diagnosability | `provider.py` retains `stderr_excerpt` / `stderr_text` on FAIL; `test_driver.py` 12 passed |
| W1–W2 shadow harness | `compiler/tests/conformance/` fixtures 01–14, `shadow_runner.py`, `counterexamples.yaml` |
| W3 compile ingress | `compile_intent_ingress()` + `--check-input`; campaign execute still refuses `intent.v1` (intentional) |
| W7 shadow graduation | `test_graduation.py` 1 passed — zero blocking metrics on golden journeys |

**Residual (not stale defects):**

- W3: `PROGRAM_INTENT_V1` ∉ `SUPPORTED_KINDS` for campaign **execute** until a post-W8 `make campaign` plan.
- W7: Spine execute / Lock / 10-run repeatability not proven; `make campaign` was not invoked.
- **W4 reopened (A3):** lowercase materiality is closed in `architecture_intent.normative_signals()`
  but **not** in `architecture_extractor._sentence_kind()`, whose `_KIND_RULES` are uppercase literals
  matched with `signal in sentence` — no `lower()`, no `IGNORECASE`. Probe at `450b7d0e`:
  `normative_signals("the resolver must preserve …")` → `('MUST','PRESERVE')`, while
  `_sentence_kind(...)` → `None` (uppercase → `requirement`). Two vocabularies; AT-002/AT-003 are
  not closed on the deterministic surface, which is the surface tests force.
- **W5 reopened (A4):** `repo_truth.classify_dispositions()` has **zero production callers** — only
  `test_repo_truth.py` and `tests/conformance/shadow_runner.py`. The live lowerer
  `architecture_to_campaign.py` uses its own `RepositoryFacts` / `_resolve_paths` (exists vs proposed).
  CE-AT-005/006 are closed **in shadow only**; the live path is unproven.

---

## External audit reconciliation (2026-08-31)

Two operator microscope audits (`Pec1.md` compiler seam, `Pec2.md` Blueprint→execution seam) were
reconciled against baseline `450b7d0e`. **Every claim below was re-verified in code before being
recorded here — none is carried on the audit's word.** 18 discrete findings.

| Verdict | Count | Share |
| --- | --- | --- |
| **Additive** (not tracked by this pipeline) | **14** | **78%** |
|  └ fully new | 12 | 67% |
|  └ sharpens an existing W8/S6 bullet | 2 | 11% |
| Already covered (confirms landed W0–W7) | 4 | 22% |

Per document: **Pec1 50% additive** (4/8 — it audits the compiler front half W0–W7 already closed,
so half is confirmation). **Pec2 100% additive** (10/10 — it audits the Blueprint→execution seam this
pipeline never covered; it is precisely the W7 residual "spine execute / Lock not proven").

### Additive — compiler seam (Pec1)

| ID | Finding | Sev | Evidence at `450b7d0e` |
| --- | --- | --- | --- |
| A3 | Deterministic extractor loses lowercase obligations | P1 | `_sentence_kind()` → `None` for lowercase, `requirement` for uppercase; `normative_signals()` returns `('MUST','PRESERVE')` for both |
| A4 | `repo_truth` dispositions never reach live lowering | P1 | `classify_dispositions` callers: `test_repo_truth.py`, `shadow_runner.py`. Zero production |
| A5 | Unmarked dense `.md` silently routes to brief compiler | P2 | By design; audit asks for a warn-don't-steal diagnostic, not auto-detection |
| A8 | Compiler README overstates the failure set | P3 | README:154 "fails … **only** for" 4 conditions; lowerer also raises at `architecture_to_campaign.py:264` and `:516` |

### Additive — Blueprint→execution seam (Pec2), previously untracked

| ID | Finding | Sev | Evidence at `450b7d0e` |
| --- | --- | --- | --- |
| B1 | Launchability gate is a no-op on native Blueprints | **P0** | `blueprint_tasks()` reads `tasks.json` / `tasks/*.json` (launchability.py:325). Probe: a `TASK_CARDS.yaml` with 1 task → **0 tasks**; `check_launchability` then returns `launchable: True, skipped: no_task_cards` (run_campaign.py:2294). The writer at launchability.py:296 speaks `TASK_CARDS.yaml` — reader and writer disagree inside one file |
| B2 | Normal execution rewrites accepted Blueprint authority | **P0** | `fill_inferred_validation()` (run_campaign.py:2408) writes `TASK_CARDS.yaml`, then relocks and rematerializes |
| B3 | Explicit-task-id relock bypasses the drift classifier | **P0/P1** | `relock_definitions(task_ids=…)` (controller.py:369) skips `stale_task_ids()`; its docstring makes the bypass deliberate, but the automatic late-repair caller supplies ids without doing the comparison the docstring assumes |
| B4 | Mutating `repo_local` task may pass with inspection-only validation | P1 | No `repo_local + local_write ⇒ terminal verifier` rule at compile or admission |
| B5 | Program Lock flattens the validation algebra | P1 | `required_commands` keeps only `{command, command_and_inspection}` (blueprint.py); `inspection` / `external_adapter` drop out. *Sharpens W8/S6 "validation adapter path semantics"* |
| B6 | Contracts treat zero validators as complete | P1 | `source-contract.schema.json` `validation_commands.minItems: 0` |
| B7 | No `missing_terminal_verifier` blocker | P1 | Absent from readiness and preflight. *Sharpens W8/S6* |
| B8 | Late writer emits a schema-invalid card, destructively | P1 | Entry omits `environment` (schema requires `id, method, command_or_inspection, environment, expected_result` — validated: `'environment' is a required property`), and **replaces** `task["validation"]` rather than appending. Launchability's own writer does set `environment`, so this is specific to `run_campaign` |
| B9 | Repairing B1 exposes a MANIFEST transaction-order problem | P1 | Launchability mutation is manifest-governed; revalidation currently precedes manifest regeneration. Not executed — reasoned from sequencing |
| B10 | Launchability fixtures assert a dead vocabulary | P2 | `test_launchability.py` uses `repo_change` / `analysis`; native enum is `program_control, repo_local, external_adapter, read_only` |

### Already covered — no action (confirms landed work)

A1 BLOCKED-Blueprint pathology repaired · A2 unknown seam fabricates no write authority ·
A6 minimal `intent.v1` stays strict by design · A7 coverage/provenance strict in the right place.

### Harvested — target lifecycle (Pec2)

The audit's correction is not "make the executor better at patching Blueprints"; it is to make
execution completeness a **compile/admission** property:

```text
operator intent → compiler → native Task Cards
  → PRE-SEAL EXECUTION COMPLETENESS
      ├─ derive deterministic validators where authority permits
      ├─ preserve all original validation semantics
      ├─ resolve typed verification mechanisms
      └─ fail if mutating work remains unverifiable
  → regenerate MANIFEST → canonical Blueprint validation → accept/seal
  → bootstrap immutable Program Lock → Source Contracts → Rendered Contracts
  → readiness / claim → workers
```

**Governing invariant:** after accept/seal, `Blueprint write count = 0` during ordinary execution.
Not "few", not "only validator fixes" — zero. A genuinely new fact becomes an explicit superseding
Blueprint revision with provenance, never an implicit runtime patch.

**Diagnosis:** two definitions of "Blueprint complete" coexist. Compile/accept says *"the task has a
validation object"*; execution says *"I need an executable validation command"*. Neither is wrong
alone — the bug is that they are reconciled **after acceptance, during execution**.

**Restart cost of that reconciliation:** invalidate → adopt → re-lock → re-materialize → re-claim →
re-prepare → re-render → re-start, paid **per task**. That is the mechanical explanation for a
campaign that appears to prepare itself forever instead of doing work.

**Typed replacement for the lossy field** — `required_validation_commands: list[str]` should become
`verification_mechanisms` as a tagged union (`command` / `inspection` / `external_adapter`) with
exact evaluator and admission semantics per kind. Do not cross a major architecture boundary by
reducing a tagged union to a list of strings.

**Required invariant for explicit scoped relock** (B3) — even with explicit task ids: all
non-task-definition source digests MUST equal the previous lock; task membership MUST be unchanged;
all non-selected task definitions MUST hash identically. Scoped adoption may then update only the
digest of the legally changed source, never opportunistically refresh every Blueprint digest.

### Harvested — remediation order (Pec2 "what I would change in code")

| Pri | Change | Why |
| --- | --- | --- |
| P0 | Replace `launchability.blueprint_tasks()` with the canonical native `TASK_CARDS.yaml` parser used by Controller/compiler | Eliminate the native/legacy adapter split (B1) |
| P0 | Delete the normal-execution Blueprint-write branch from `fill_inferred_validation()` | Runtime must not mutate sealed authority (B2) |
| P0 | Make `post_accept_blueprint_write_count != 0` a fatal invariant violation | Turns architecture law into executable law |
| P0 | Harden explicit scoped relock against all non-selected source drift | Prevent mixed-version locks / digest laundering (B3) |
| P1 | Introduce typed `verification_mechanisms` across Blueprint → Lock → Source → Rendered | Stop losing inspection / external_adapter semantics (B5) |
| P1 | Require a terminal verification mechanism for every mutating `repo_local` task before acceptance | Catch incomplete execution semantics at the right stage (B4) |
| P1 | Run execution-completeness enrichment **before** final MANIFEST generation | Avoid post-validation mutation (B9) |
| P1 | Store launchability/admission reports outside the sealed Blueprint, or create them before the final manifest | Keep immutable-source accounting exact (B9) |
| P1 | Remove destructive validation-list replacement; enrich canonically | Preserve operator completion semantics (B8) |
| P1 | Require canonical Blueprint schema validation after every pre-seal mutation | Stop invalid source being laundered through normalization (B8) |
| P2 | Delete legacy `repo_change` / `analysis` / `tasks.json` launchability fixtures | Tests assert a dead vocabulary (B10) |
| P2 | Put `missing_terminal_verifier` into Controller readiness/preflight | Defence in depth (B7) |
| P2 | Assert `compiled_task_count == launchability_task_count == program_lock_task_count` | Instantly catches adapter disconnects (B1 class) |

### Harvested — proof tests (Pec2)

The strongest end-to-end regression is nearly trivial, and had it existed the pathology could not
have hidden:

```text
blueprint_digest_at_acceptance = sha256(all Blueprint bytes)
run entire campaign
assert sha256(all Blueprint bytes) == blueprint_digest_at_acceptance
assert normal_execution_relock_count == 0
```

| Test | Required assertion |
| --- | --- |
| Native compiled campaign → launchability | tasks read from `TASK_CARDS.yaml` == compiler task count |
| `repo_local` + `local_write` + inspection-only | cannot reach acceptance/bootstrap without an authorized terminal verifier |
| `read_only` + inspection-only | remains valid — do not over-tighten discovery/audit work |
| Pre-seal inferred validator | canonical Task Card stays schema-valid; existing validations preserved |
| Pre-seal mutation + MANIFEST | final tree/hash inventory validates exactly once after enrichment |
| Full multi-task campaign | Blueprint byte-identical from acceptance through completion |
| Full multi-task campaign | `normal_execution_relock_count == 0` |
| Missing runtime verifier | structured blocker before worker launch — not a source rewrite |
| `external_adapter` validation | survives Blueprint → Lock → Source → Rendered without disappearing |
| Explicit task relock + AUTHORITY_MAP drift | relock refused |
| Explicit task relock + gate/evidence/program drift | relock refused |
| Explicit scoped relock | non-selected source digests cannot be silently refreshed |
| Fixture hygiene | every execution kind used in tests belongs to the current Task Card enum |
| Provider boundary | worker/provider has no capability to modify accepted Blueprint authority |

### Harvested — compiler seam remediation + scorecard (Pec1)

Three changes, in order:

1. **P1 — collapse normative lexical semantics into one implementation.**
   `architecture_intent.normative_signals()` becomes the deterministic extractor's canonical signal
   source. Add live E2E fixtures with lowercase `must`, `must not`, `don't`, `never`, `preserve`,
   "keep the existing…", "reuse the current…", run through
   `compile_architecture_intent(..., extractor=deterministic)`, requiring coverage PASS plus correct
   task/prohibition semantics. One parser, one vocabulary, one semantic law.
2. **P1/P2 — wire repository dispositions into `architecture_to_campaign.lower()`.** Carry `KEEP`,
   `HARDEN_WIRE_EXISTING`, `MERGE_WITH_EXISTING`, `CREATE` into semantic provenance and action
   formation rather than only discovering whether a path exists. Then promote the W5 shadow cases
   into real architecture-compiler E2E fixtures.
3. **P2 — add route-confusion diagnostics.** Keep generic Markdown → brief deterministic, but when
   ordinary `make campaign` sees high architecture/normative density, tell the operator that
   `campaign-architecture` exists. **Warn, don't steal** — never silently reinterpret, never
   silently push a rich document through a weaker compiler.

| Dimension | Score | Note |
| --- | --- | --- |
| Rich intent rejected because schema too narrow | 9/10 | dedicated architecture route is the right structural fix |
| Unknowns create BLOCKED Blueprint cards | 10/10 | evidence-task/dependency treatment repaired |
| Unknown implementation location handling | 10/10 | ready + inspection-only + zero invented write authority |
| Semantic fidelity / no-loss architecture | 8.5/10 | provenance and coverage strong |
| Natural-language deterministic acceptance | **6/10** | the A3 extractor split undermines the W4 claim on fallback surfaces |
| Repository reconciliation | **6.5/10** | disposition intelligence exists but sits in shadow, not the live lowerer (A4) |
| Conformance confidence | **7/10** | golden architecture E2E is meaningful; the W4/W5 shadow suite must not declare closure for behavior it never executes |

**Operator front door for dense material** (not the minimal `intent.v1`):

```bash
make -C "$HOME/.cursor-governance" campaign-architecture \
  INTENT=/path/to/microscope-audit.md TARGET=owner/repo
```

Accepted through that route without rewriting: dense architecture documents, microscope audits,
technical reviews, implementation plans, prose+tables+code fences, very long documents (whole-unit
chunking), documents with no task list, "we need to determine whether X" (→ ready read-only
discovery), requirements with no known implementation path (→ inspection-only, no fabricated
target), no explicit test command, and explicit OUT OF SCOPE deferrals (preserved as exclusions).
Still refused by design: `program-execution.intent.v1` carrying tasks/files/waves/prompts;
internally contradictory equal-authority obligations; wholly non-executable prose.

### Disposition

B1–B3 are the highest-leverage items in this file: they explain a campaign that "prepares forever",
and B1 is a one-line-looking reader bug that **B9 says must not be fixed one-line**. A3/A4 mean the
W4/W5 rows above read "Complete" for a contract that is delivered but not integrated — the shadow
harness is green on paths the live compiler does not take.

**None of this is authorized work here.** W8+ still requires its own plan on a fresh `origin/main`
SHA. Recorded so that plan starts from verified truth instead of re-deriving it.

---

## Next: W8 (v3 control-plane)

Start only via a new plan after W7 lands on `origin/main`. Do not reopen the W0–W7 Build.

### W8 prep (from PE-PE 1 — harvested 2026-08-30)

- **v3 surfaces:** `program-execution-system.v3`, `program-execution-blueprint.v3`, `program-execution-controller.v3`; v2 receipts stay v2 forever.
- **Two planes:** pinned v2 orchestrator checkout (A) orchestrates repair of editable implementation (B). Freeze **fresh** baseline at W8 start — `0db3fed` in the v2 registry is forensic only.
- **S0 counterexamples SSOT:** [`environment/program-execution/conformance/counterexamples/v2-gaps-registry.yaml`](../../../environment/program-execution/conformance/counterexamples/v2-gaps-registry.yaml) — S8 exit = zero hardening xfails.
- **S1 semantic conservation:** `PROGRAM_SEMANTICS.yaml` canonical model; projections derive from SemanticModel; split semantic prohibitions from `filesystem_scope` paths.

See [`PEC-repair-pipeline.json`](./PEC-repair-pipeline.json) W8 `subwaves` for S0–S8 acceptance bullets.

### Campaign activation (when W8+ admits campaigns)

Use live skill **`skills/l9-pe-campaign-activate`** — not WIP template copies under `_archive/`.

---

## Already done — do not rebuild

- Compiler module in-tree (`environment/program-execution/compiler/**`).
- W0–W7 spine (commit `e8785018`).
- Campaign front door for brief / plan / activate / campaign-source.v2 / architecture-intent.
- `run_campaign.py` `refuse_publication` — runner cannot push, open, or merge.
- Campaigns: `bounded-replanning-v1` (PR 149), `l9-devpack-program-execution-hardening` (PR 150) — CONVERGED;
  `level3-make-pr-single-path` (PR 187) — CONVERGED_WITH_NON_BLOCKING_RISKS (ledger's own string).
- `cc-pe-intent-compiler-v1` — registered/archival; not the graduation test.
- Skill `l9-pe-campaign-activate` — live.
- Graphiti is resume SSOT.
- **Tracker-truth fixes (2026-08-31, `ead6d6f`)** — closed, do not re-raise: Build-plan link
  depth corrected (`../../` → `../../../`); `_archive/DEPRECATED.md`'s "are gone" claim recorded as
  never-true (archive is `must_not_modify`, so the correction lives here); level3 verdict restored to
  the ledger's `CONVERGED_WITH_NON_BLOCKING_RISKS`; `T-W1-fixtures` repointed from the nonexistent
  `schema_semantic_expectation.json` to the landed `conformance/expectation.py`.

---

## Parked — not this pipeline

| Item | Why it is out |
| --- | --- |
| Environment-experience 8-release brief | Different program. Failed run is W0 evidence only. |
| Perplexity PR pack v2 | Host overlay after W7. |
| PE Memory cutover docs | Later, if W7 still lacks evidence/memory projection. |
| Draft `canonical.schema.*.yaml` family | Live plan schema: `skills/l9-plan/schemas/plan-document.schema.json`. |
| `pe-v3-hardening` campaign source | Forensic, `operator_intake`. W8 takes its *intent*, fresh baseline. |
| `WIP/PROGRAM EXECUTION PIPELINE/` | Harvested into W8 prep 2026-08-30; deleted. |

---

## How to execute W8+ (when authorized)

Every W8 job remains a bootstrap pack, not a chat prompt:

```text
bootstrap/<work-id>/
  00-source-intent.md     # immutable, hashed
  01-intent-ir.yaml
  02-grounding.yaml
  03-requirements.yaml
  04-execution-contract.yaml
  05-evidence/
  06-completion.yaml
```

Stop on `CONTRACT_DRIFT`. Do not invent a second controller, transport, replanner, authorization model, or evidence model.

W8 uses two planes: pinned v2 orchestrator (A) vs editable implementation (B).

---

## Graduation (W7 done) — dogfood (W10)

W7 shadow graduation is complete when golden-journey blocking metrics are zero (see `test_graduation.py`). Full spine execute/Lock/repeatability is a W8+ concern.

W10 is trusted enough for Risk-bearing work when PEC, given the original messy RiskPacket request, concludes on its own: harden replanner, preserve auth/evidence/Gate, create ImpactEngine + RiskPacket, duplicate nothing.

---

## If you must hand-author `campaign-source.v2`

Prefer the brief/intent route or `l9-pe-campaign-activate`. If it fails, the archived HANDOFF gotchas still hold: `plan_status`, `risks[].owner`, admitted `input_evidence_ids` only, per-task `paths:`, single-op validation commands, numeric TASK/GATE ids, never reuse a failed `campaign_id`.
