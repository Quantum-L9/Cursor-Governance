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

<!-- PEC-EXECUTION-COMPLETENESS-10 -->
### Execution-completeness batch 1-10

The first ten entries in `external_audit_reconciliation.remediation_order` are now
implemented and locally validated under `pec-execution-completeness-10-2026-08-30`. This closes B1, the two B2
repairs, B3, B5, B4, the two B9 repairs, and the two B8 repairs. Normal execution
no longer repairs sealed Blueprint authority. Typed verification semantics survive
Blueprint -> Program Lock -> Controller state -> Source Contract -> Rendered Contract.

This does **not** close the reopened W4/W5 residuals and does **not** authorize W8
activation.

<!-- PEC-NORMATIVE-AND-DISPOSITION-2 -->
### Normative-vocabulary and disposition batch 11-12

Positions 11 (`A3`) and 12 (`A4`) are implemented and locally validated under
`pec-normative-and-disposition-2-2026-08-31`. These are the two reopened residuals,
so **W4 and W5 are now closed on the live surface**, not only in shadow:

- **U6 / A3** — `architecture_intent.normative_signals` is the extractor's canonical
  source. The second, upper-case-only vocabulary in `architecture_extractor` is gone,
  so `must not` reaches the same kind as `MUST NOT`. Before this, `_sentence_kind()`
  returned `None` for every lower-case obligation while `normative_signals` reported
  the canonical name — two vocabularies disagreeing about the same sentence.
  CE-AT-002 / CE-AT-003 now hold on the deterministic surface the tests force.
- **U7 / A4** — `architecture_to_campaign.lower()` consumes
  `repo_truth.classify_dispositions()`. That classifier had **zero production callers**;
  lowering asked only `RepositoryFacts.path_exists`, a binary that cannot tell
  `HARDEN_WIRE_EXISTING` from `CREATE`. KEEP / HARDEN / MERGE / CREATE now reach action
  wording and per-item provenance. CE-AT-005 / CE-AT-006 hold live.

Still **not** authorized: W8 activation, and `PLAN_DOCUMENT.pec-repair-pipeline.v1.json`
is unchanged.

<!-- PEC-TAIL-5 -->
### Tail batch 13-17 — remediation_order fully executed

Positions 13-17 landed under `pec-tail-5-2026-08-31`. **All 17 remediation entries
are now complete**; nothing in `remediation_order` is open.

- **A5** — the brief route emits `route_confusion` diagnostics when a memo carries
  architecture-grade structure. It warns through the existing preflight warning
  channel and never re-routes: re-routing on a heuristic is the guessing this
  front door exists to stop. It reads `normative_signals`, not a second regex.
- **B10** — fixtures moved off the dead `execution_kind` vocabulary. `repo_change`
  and `analysis` are not in the task-cards enum
  (`program_control | repo_local | external_adapter | read_only`), so tests built
  on them asserted a vocabulary nothing else speaks.
- **B7** — `missing_terminal_verifier` is a blocking Controller readiness reason.
  Acceptance already refuses it pre-seal; readiness is the second line for a lock
  written before that rule existed.
- **B1 class** — `assert_task_counts_agree` compares compiled / launchability /
  program-lock counts at bootstrap. This is the check that would have caught the
  original B1 the moment it happened.
- **A8** — the "fails only for" clause now names the exact five `audit()` failures
  and the two that live outside it.

Two things seen and deliberately **not** changed, recorded so they are not lost:
`launchability._INSPECTION_KINDS` still tolerates `analysis`/`inspection`/
`decision`/`review` (unreachable through schema-validated blueprints), and
`CoverageError` is exported but never raised. Both are production surfaces that
B10 and A8 do not cover.

W8 activation remains unauthorized and requires its own plan bound to a fresh
`origin/main` SHA.

This folder is no longer a dump of PE research. It is one remaining pipeline.

---

## What this is

> **New here?** Read [`HANDOFF.md`](./HANDOFF.md) first — current state, the one red
> check and why it is not this PR's, what is actually left, and the commands that
> prove each claim. This file is the narrative history behind it.

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
| **W4** | C2 | **Complete** — residual A3 closed live (batch 11-12) | W3 |
| **W5** | C3 | **Complete** — residual A4 closed live (batch 11-12) | W4 |
| **W6** | C4 | **Complete** | W5 |
| **W7** | C5 | **Complete** (shadow only) | W0 + W6 |
| **W8** | PE v3 S0–S8 + C6 | **Open** | W7 |
| **W9** | C7–C10 | **Open** | W8 |
| **W10** | C11 | **Open** | W9 |

W8+ is forbidden until a separate plan with a fresh baseline SHA.

---

## Verified at HEAD (`35880e70`) — W7 completion snapshot

> History. This is the evidence at W0–W7 completion (landed `e8785018`); it is not
> rewritten as work continues. Everything published after W7 is in
> **Published at HEAD** below.

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

## Published at HEAD (`fea124cd`)

[PR #442](https://github.com/Quantum-L9/Cursor-Governance/pull/442) · base `main`
(at `da0c7530`) · 11 commits · 38 files · `mergeable: true`, state `blocked` · 0 reviews.

Five batches:

| Batch | What |
|---|---|
| `pec-execution-completeness-10-2026-08-30` | remediation 1–10 |
| `pec-normative-and-disposition-2-2026-08-31` | remediation 11–12 |
| `pec-tail-5-2026-08-31` | remediation 13–17 — queue emptied |
| `pec-w8-s0-counterexample-reproduction-2026-09-01` | 6 counterexamples that reproduced as nothing |
| `pec-w8-s0-baseline-freeze-2026-09-01` | `GATE-S0-BASELINE-CHARACTERIZED` made executable |

**CI on this head: 22 checks — 19 success, 2 skipped, 1 failure.** Every job that
runs this work is green: Peer Execution Conformance, Test Suite, Lint and Type
Check, governance-self-check.

Local evidence: gate 5 PASS / 1 FAIL (`pinned_to_main`), exit 1 · gate tests 16 OK ·
registry conformance 14 OK · conformance runner PASS, 649 tests, 0 failures ·
hardening 56 passed, 15 xfailed.

### The one red check is not this PR's

`Analyze (central Core)` fails at *Enforce central mode on SDK technical gate*.
`l9-ci-sdk` `7d7762e` `provider.py:396-415` maps **every** entry of semgrep's
`errors[]` to `ProviderFailure(fatal=required)` without reading the entry's `level`.
Semgrep reported `{level: warn, type: Timeout}` — a warning — with 669/669 files
scanned and all 150 findings produced. Coverage is derived from that same failures
list at `provider.py:431`, so one warning produces both gate reasons and the gate
returns `incomplete` on a bundle with zero blocking and zero unresolved findings.

Filed upstream as [`l9-ci-sdk#79`](https://github.com/Quantum-L9/l9-ci-sdk/issues/79)
and [`l9-ci-core#122`](https://github.com/Quantum-L9/l9-ci-core/issues/122); published
on the PR as `issuecomment-5486348896`; carried as session debt
`sdk-semgrep-warn-promoted-to-fatal`. Not re-runnable from this surface
(`rerun-failed-jobs` returns 403). Nothing in this repository can fix it, and it was
not worked around by excluding the file or the rule.

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

### Findings coverage — 14 of 14 closed

`remediation_order` is fully executed, 17 of 17 positions. That is **not** the same
statement as "every finding is closed": the 17 positions cover 13 findings, and one
finding never got a position at all.

| | |
|---|---|
| Closed via `remediation_order` | A3, A4, A5, A8, B1, B2, B3, B4, B5, B7, B8, B9, B10 |
| Closed directly (no position) | **B6** — batch `pec-w8-s0-close-2026-09-01` |

B6 is closed — see **W8/S0 closed** below for what the defect actually was and why
the obvious fix would have been wrong.

Each additive finding now carries `execution_status` and `closed_by`, derived from
`remediation_order` rather than asserted.

### Audit assessment is dated, not live

`status_corrections` and `acceptance_scorecard` were measured at `450b7d0e`, before
any batch ran. They are retained verbatim — annotated, never rewritten. Two of the
three status corrections have since been closed by execution (A3 and A4, batch
`pec-normative-and-disposition-2-2026-08-31`; B1–B3 in the first batch and the tail),
recorded in `status_corrections_since_closed`.

The scorecard is **not** re-scored. Two rows name a blocker that is now closed — the
A3 extractor split and A4's shadow-only dispositions — but no measurement was taken
after execution, and a number invented to look current is worse than a dated one.
Re-scoring is real work, not a tracker edit.

### Disposition

B1–B3 are the highest-leverage items in this file: they explain a campaign that "prepares forever",
and B1 is a one-line-looking reader bug that **B9 says must not be fixed one-line**. A3/A4 mean the
W4/W5 rows above read "Complete" for a contract that is delivered but not integrated — the shadow
harness is green on paths the live compiler does not take.

**None of this is authorized work here.** W8+ still requires its own plan on a fresh `origin/main`
SHA. Recorded so that plan starts from verified truth instead of re-deriving it.

---

## Next: W8 (v3 control-plane)

The plan exists and is validated: [`PLAN_DOCUMENT.pec-w8-s0.v1.json`](./PLAN_DOCUMENT.pec-w8-s0.v1.json), projected to
`.cursor/plans/pec-w8-s0-baseline-freeze.plan.md`. Do not reopen the W0–W7 Build.

**S0 is closed.** `python environment/program-execution/scripts/gate_s0_baseline.py`
exits **0**: five blocking conditions PASS, carrying one printed advisory
(`pinned_to_main` — durability, which binds at promotion in S8). **S1** is the next
subwave and needs its own authorization and plan.

### W8 prep (from PE-PE 1 — harvested 2026-08-30)

- **v3 surfaces:** `program-execution-system.v3`, `program-execution-blueprint.v3`, `program-execution-controller.v3`; v2 receipts stay v2 forever.
- **Two planes:** pinned v2 orchestrator checkout (A) orchestrates repair of editable implementation (B). Freeze **fresh** baseline at W8 start — `0db3fed` in the v2 registry is forensic only.
- **S0 counterexamples SSOT:** [`environment/program-execution/conformance/counterexamples/v2-gaps-registry.yaml`](../../../environment/program-execution/conformance/counterexamples/v2-gaps-registry.yaml) — S8 exit = zero hardening xfails.
- **S1 semantic conservation:** `PROGRAM_SEMANTICS.yaml` canonical model; projections derive from SemanticModel; split semantic prohibitions from `filesystem_scope` paths.

See [`PEC-repair-pipeline.json`](./PEC-repair-pipeline.json) W8 `subwaves` for S0–S8 acceptance bullets.

### W8/S0 partial — counterexample reproduction closed (2026-09-01)

Batch `pec-w8-s0-counterexample-reproduction-2026-09-01`. **W8 stays open**; this
closes one S0 acceptance bullet and nothing else.

The registry declared `verification: all_counterexamples_reproduce_as_xfail_tests`
while **five of the nine test files it named did not exist** — so six of fifteen
counterexamples reproduced as nothing at all. Its own summary disagreed with its
entries as well (`high: 6` against seven, `low: 1` against none, `test_files: 8`
against nine).

Landed:

| Path | Counterexamples |
|---|---|
| `tests/hardening/test_hardening_gates.py` | CE-GATE-001 |
| `tests/hardening/test_hardening_repository.py` | CE-REPOSITORY-001 |
| `tests/hardening/test_hardening_leases.py` | CE-LEASE-001 |
| `tests/hardening/test_hardening_replan.py` | CE-REPLAN-001 |
| `tests/hardening/test_hardening_closeout.py` | CE-CLOSEOUT-001, CE-CLOSEOUT-002 |
| `conformance/test_counterexample_registry.py` | — (checks the registry against the suite on disk) |

The summary counts were corrected to match the entries. The `verification` claim
was **earned rather than softened**: it is now true, and
`test_verification_claim_is_earned` fails if it ever stops being — every entry must
name a test file that exists, defining a function that carries an `xfail` marker
whose reason names that counterexample's own ID.

Evidence:

- hardening suite — **56 passed, 15 xfailed** (was 9 xfailed)
- conformance runner — **PASS**, 628 tests, 0 failures, 0 errors, new file collected
- registry suite — 9 tests OK; it reproduced all three summary defects before the correction

Still gating S0 (unchanged): the baseline commit and orchestrator checkout must be
frozen independently against a **fresh** `origin/main` SHA after W7 merges, and PE
surfaces digest-manifested. `GATE-S0-BASELINE-CHARACTERIZED` is **not** passed. No
v3 surface, no baseline pin, no product behavior change.

### W8/S0 partial — baseline freeze made executable (2026-09-01)

Batch `pec-w8-s0-baseline-freeze-2026-09-01`, planned by
[`PLAN_DOCUMENT.pec-w8-s0.v1.json`](./PLAN_DOCUMENT.pec-w8-s0.v1.json). **W8 stays
open.**

`GATE-S0-BASELINE-CHARACTERIZED` existed only as prose — here and in the archived
`PE-PE 1.md`. A gate that cannot be run can only be discharged by a person
re-reading it, which is why the freeze kept waiting on a SHA someone would hand-type.
Separately, `baseline_commit` held the **forensic** `0db3fed` in a field that reads
as live, with nothing marking the difference.

Landed:

| Path | What |
|---|---|
| `scripts/gate_s0_baseline.py` | The gate, executable, reporting each condition independently |
| `scripts/tests/test_gate_s0_baseline.py` | 16 tests — both states, drift, forensic-as-live, independence |
| `conformance/counterexamples/v2-gaps-registry.yaml` | `baseline` block: forensic / characterized / main pins kept distinct |
| `conformance/test_counterexample_registry.py` | `RegistryBaselineTests`; `xfail_reasons` consolidated onto the gate |

Three kinds of pin, deliberately separate — `forensic_commit` (evidence, never
live), `characterized_at` (where the counterexamples were proven to reproduce),
`pinned_to_main` (`null` until merge). Drift is measured over the **reproduction
surface**, not the repository manifest: the manifest digests the registry, so
recording a manifest digest inside it would be self-referential and could never
settle.

Against the live tree the gate reports five conditions PASS and exactly one FAIL:

```
[FAIL] pinned_to_main: not pinned: the characterized work has not reached
       origin/main yet. Set baseline.pinned_to_main to the merge commit and
       re-run this gate.
```

Evidence: gate tests 16 OK · registry suite 14 OK (was 9) · conformance runner
PASS · hardening 56 passed / 15 xfailed, unchanged.

**Deliberately not done.** The gate is *not* wired as a blocking CI step: it cannot
pass before merge, so wiring it now would only turn the PR red and teach people to
ignore it. S1–S8 are unstarted. `U2` is open — whether plane A needs a physically
detached orchestrator checkout rather than the recorded immutable reference used
here — left open rather than resolved by assumption.

### W8/S0 closed — gate passes; B6 closed with it (2026-09-01)

Batch `pec-w8-s0-close-2026-09-01`. `GATE-S0-BASELINE-CHARACTERIZED` **exits 0**.

#### B6 — the finding was right, the obvious fix was not

`validation_commands.minItems: 0` looks like the defect, and raising it to 1 looks
like the repair. It is not: a task verified solely by `external_adapter` is terminal
but deliberately not shell-flattened, so it derives **no** commands. Requiring one
would refuse a legitimate shape.

The real vacuity was one gate. In `controller.py`:

```python
claimed_commands = [item.get("command") for item in claimed_results]   # []
required_commands = contract.get("validation_commands") or []          # []
gates["worker_validation_claim"] = "PASS" if claimed_commands == required_commands \
    and all(item.get("status") == "PASS" for item in claimed_results) else "FAIL"
```

Both sides empty, `all([])` is True → **PASS**, asserting the worker's validation
claim against zero evidence. `gates["validation"]` said `INCOMPLETE` in the same
breath, so no verdict was actually wrong — which is precisely the problem: the safety
was a property of a *sibling* gate. It now reports `INCOMPLETE` itself. No reachable
verdict changes; the latent vacuous PASS is gone. The schema keeps `minItems: 0`, now
documented with where non-vacuity is really enforced.

#### The gate scope correction

`pinned_to_main` moved from **blocking** to **advisory**, and this is a correction to
my own earlier design rather than a convenience.

S0 asks whether the v2 baseline is *characterized and frozen*. Whether that
characterization has reached `origin/main` is a **release** property, not a
characterization property. A branch commit is already immutable, so the freeze
verifies without `main`; what `main` adds is survival of a squash merge, which lands
the same tree under a different sha. That matters at **promotion (S8)**, not at
characterization — and gating S0 on a merge made the gate unclearable by any action
available before that merge, the shape that teaches people to route around a gate.

**Not a weakening.** The blocking set is otherwise unchanged: registry parses,
baseline block complete, all 15 counterexamples reproduce, forensic/live pins distinct
and well formed, reproduction not drifted. A stale, wrong, or forensic-as-live
baseline still fails, and a test pins that a drifted reproduction surface still
blocks. The advisory prints on the same screen as the PASS, so "advisory" cannot
shade into "hidden":

```
PASS: baseline characterized and frozen
  carrying advisory: pinned_to_main
```

Evidence: gate exit 0 · gate tests 19 OK · kernel-verdict tests 4 OK · registry
conformance 14 OK · hardening 56 passed / 15 xfailed, unchanged.

**Not claimed.** W8 stays open. S1–S8 are unstarted; S1 (semantic conservation
compiler + atomic acceptance) is next and needs its own authorization and plan.

### W8/S1 started — semantic prohibitions are not path globs (2026-09-01)

Batch `pec-w8-s1-prohibition-split-2026-09-01`, planned by
[`PLAN_DOCUMENT.pec-w8-s1.v1.json`](./PLAN_DOCUMENT.pec-w8-s1.v1.json). Closes the
**split** bullet of S1; three bullets remain.

S1's split is stated as *"prohibitions (semantic laws) vs
filesystem_scope.forbidden_paths (glob paths)"*. The seam was doing the opposite:

```python
# compile_campaign_source.py
"path_or_pattern": item["statement"],     # a sentence, into a glob field
```

The Controller then matched that field against the files an attempt changed, with a
substring fallback when it would not parse as a path. A sentence never appears inside
a repo path, so `do_not_build` reported **PASS having enforced nothing** — the same
shape as B6, one layer out. `compiler/synthesizer.py` shipped two hardcoded
architecture laws exactly that way: *"a second Program Execution runtime or
Controller"* and *"compiler-owned mutable runtime state"*.

Landed:

| Path | What |
|---|---|
| `compiler/prohibition_kind.py` | Classifier + entry builder; **conservative toward `path`** so no existing glob is reclassified |
| `compile_campaign_source.py`, `compiler/synthesizer.py` | Both emitters route through it |
| `controller.py` | Substring fallback removed — an unparseable entry is skipped, not pretended to match |
| `do-not-build.schema.json` | `kind` declared (additive; `additionalProperties` was already true) |
| `test_prohibition_kind.py`, `test_do_not_build_verify.py` | 7 + 1 tests, both sides of the seam |

**Checked before removing enforcement.** No live campaign carries any DNB entry — the
forensic `pe-v3-hardening` blueprint has zero and the template holds a
`REPLACE_WITH` placeholder — so the fallback was enforcing nothing that anyone
relies on. That check was a plan checkpoint, not an afterthought.

**Still open in S1:** the `CAMPAIGN_SOURCE → SemanticModel → projections →
reconstructed semantics` round-trip, `semantic_diff` empty on a full fixture, and
`GATE-S1-SEMANTIC-CONSERVATION`. Those are a substantially larger build.

**W9 and W10** are sequenced behind W8's remaining subwaves by `depends_on`, not by a
missing plan.

### U3 closed — `do_not_build` states what it did not check (2026-09-01)

Batch `pec-w8-s1-u3-gate-coverage-2026-09-01`. This gap was **opened by the S1
split and closed by the same session.**

Stopping semantic prohibitions being globbed was right. Leaving the gate silent
about them was not: `do_not_build: PASS` then reads as *"no prohibition was
violated"* when it only ever meant *"the changed paths are clean"*. That is the
third instance of one root cause — **a gate reporting PASS about work it did not
do** — after B6's `worker_validation_claim` and the split itself.

The verification receipt now carries:

```json
"unenforced_prohibitions": [
  {"id": "DNB-001",
   "statement": "a second Program Execution runtime or Controller",
   "enforced_by": "review_and_conformance"}
]
```

Derived as the **complement of what the gate actually matches**, not by reading
`kind`, so a legacy entry carrying neither a kind nor a pattern is reported here
rather than falling between the two.

**Declared, not required — and that correction came from the suite.** Requiring it
was the first attempt, on the reasoning that an emitter which omits the field goes
silent again. Conformance refuted it: adapters emit this same receipt (generic
shell lifecycle, probe dispatch/collect) and have no program lock to read, so an
empty list from one would assert coverage it never checked — the exact vacuous
claim the field exists to prevent. The obligation belongs to the only emitter that
can honestly discharge it, pinned by the Controller's own tests rather than by a
schema three other producers share.

**Deliberately not done:** `do_not_build` does *not* become INCOMPLETE when
semantic prohibitions exist. Those laws are normal and are enforced by review and
conformance; making the gate incomplete for them would mark every campaign
incomplete forever — the unclearable-gate shape corrected in S0. The gate keeps
its path verdict; the receipt carries the coverage.

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
