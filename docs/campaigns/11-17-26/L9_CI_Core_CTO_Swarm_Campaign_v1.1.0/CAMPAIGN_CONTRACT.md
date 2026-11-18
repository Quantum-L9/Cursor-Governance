# Bounded execution contract

## Decision and scope

**Accepted intent:** every PR should not pay for the same exhaustive suites that can run daily. **Pilot owner:** `Quantum-L9/l9-ci-core`. The target is **less duplicate PR work at unchanged critical merge assurance**, not an arbitrary 2-minute green check. Fast time goal: 2–5 min, to be tested not promised. Nightly runs 1/day at proposed **07:17 UTC** on Core main; time is a scheduling parameter CTO may change to avoid an observed collision, recording the reason.

## Preserved invariants

- Canonical `l9.repo-execution/v2` remains exactly `{schema, facade, required_phases}`; phase list remains `setup, validate, check, test`, no new consumer fields or relaxed validation.
- `Makefile` generated `make-v1` facade remains byte exact; `Repo.mk` is Core-local owner of `repo-*` leaves.
- Required PR check names remain **Lint and Type Check; Unit tests; Repository contract; Governance validate; sdk-contract; Analyze (semgrep) / Analyze (semgrep -> SDK); Security scan / security** plus organization **Analyze (central Core)**. Do not edit required-status-check rulesets in this campaign.
- Critical CI regression coverage remains on PR: provenance, required check name binding, registry/ruleset/admission, SDK compatibility smoke, action pins, transport/gate enforcement, safe publication/merge boundaries, and failure propagation. CTO must bind these obligations to actual test cases and check producers before dispatch. The proposed fast census is a CTO-owned decision, not an agent-discovered policy change.
- Core's production `main` and pinned composite actions remain under present controls. SDK normalization, Semgrep policy, Biome, findings and immutable receipt semantics untouched.
- Full suite under `tests/**/test_*.py` still executed on Core main through a **separate, actual nightly deep job** and existing release validation.
- Missing/empty selected fast suite, an unavailable test tool, and a failing selected test must fail. An absent scheduled execution is not a passing test.
- No new CI engine, canonical schema/record, shared consumer override, authority class, or global project change.

## Carefully scoped realization

### Mandatory pre-launch test allocation and evidence

CTO first obtains the existing complete discoverable test census, test durations if available, and the current per-PR job/suite execution map. Then CTO records the **exact PR-critical cases/modules**, the exact `Unit tests` required-job workload, and the complete deep discovery command. Check that the two PR-required jobs are meaningfully distinct and that every required security/governance/regression witness is exercised by at least one blocking PR job. Known false-green witnesses and toolchain conformance cannot quietly move to nightly. The smallest safe choice wins; 2–5 minutes is an ambition, not a cap that may cut protected coverage.

The selected suite must fail on missing module, empty collection, failed assertion, or an unknown tool. If truly disjoint fast jobs cannot be created without losing a required regression, retain the overlap **with a measured justification** rather than replacing tests with a status-only check. Each leaf still must execute real tests; no placeholder.

### Carefully scoped realization

**A** exclusively owns `Repo.mk`, its parity test, `AGENTS.md`, and `docs/repository-execution-runtime.md` **together in one PR** because Core policy `repository-execution-evidence` requires them all when `Repo.mk` changes. This exception is not negotiable and cannot be satisfied by a different concurrent PR. The tracked `MANIFEST.sha256` ledger is retired and must not be regenerated as a new merge dependency. **A** changes Core `Repo.mk` to select an explicit, deterministic critical PR suite for `repo-test`; retains required `.PHONY` and unconditional recipe. Add a Core-local `test-deep` alias/target *in the same existing file* as a human/nightly entry point to the complete unchanged discovery. Update only affected self-hosting parity test(s). Fail closed if selected paths do not exist or collect zero tests. Include concrete test-set census and measured cost; do **not** use generic `pytest -q -k ...` heuristics or exclude tests by mutable branch name.

**B** changes Core `self-ci.yml` while preserving current job names and setup integrity; `Unit tests` becomes a short, meaningful, nonempty and (where safely achievable) non-overlapping selected subset rather than full discovery. It must remain a real required test job, not a pass-through. Add **one** new workflow `.github/workflows/nightly-deep.yml` because independent schedule/default-branch proof cannot be expressed safely by repurposing another owner, and update `test_self_ci_gating.py` accordingly. Schedule daily, permit main-ref manual dispatch, checkout exact run commit, use pinned Python/runtime requirements and run `test-deep` fail-closed. Avoid duplicate nightly jobs in `self-ci.yml`.

**C** adds only justified focused independent regression coverage in existing test locations verifying Core PR/full split, full corpus preservation, fail-closed empty/absent selectors, immutable checkout, and expected context production. The owners of A/B retain their own touched test files; C must not write them. If no nonoverlapping existing test owner can express a justified case, report it for CTO allocation, do not create a convenience file.

**D** updates only `docs/ACTIVATION.md` and `docs/release/rulesets/README.md` to state the observed behavior, test tier owners, workflow scheduling, current-check preservation, evidence obligations, and release status. No changes to globally canonical `.github` records.

**E** read-only challenge: map actual PR gate tests and potentially missed high-impact tests; get evidence-backed runner time baseline if accessible; find hidden cross-PR files and current-rule blockers. Report to CTO; do not edit or publish.

## Excluded

- Downstream consumer conversion (EIE, CEG, Odoo, others), fleet-wide nightly scheduler, global `org-ci.yml` execution semantics or trigger changes, SDK/transport updates, access policy, branch protection edits, automatic merge, refactor of `run-repository-verification`, and unrelated CI debt.
- Any proposal to drop SDK or Gate_SDK from consumer runtime manifests solely to speed CI.

## Stop conditions and controlled changes

If Fast would drop a known unique critical regression, retain it. If the full suite is still needed on one Core PR class (e.g. source-contract release), use the existing release/mandatory validation path or report the material exception; do not invent an unverified path-sensitive policy. If the true owner is elsewhere, document and defer. Do not widen the pilot to consumers. If tests or live ruleset contradict assumptions, CTO holds the affected lane and routes to its original owner.

## Dependency and admission discipline

- **Only hard coding dependency:** B consumes A's `Repo.mk` fast/deep targets and stacks onto A's pushed exact branch. A's PR retains the original full `Unit tests` job and may remain expensive: no speed claim until B lands.
- C may stack onto B if its fault witnesses exercise B's new behavior, else onto the earliest sufficient base. D may stack onto B for implementation-accurate docs; D does **not** wait for C merely because C exists. C and D never write the same files.
- Keep reviewable PRs separately green on their **declared base and current head**. A parent failure is repaired by its original PR owner; child PRs cannot launder parent failures. Never treat a green child as proof that a stale parent is green.
- Scope expansion to `org-ci.yml`, its pinned verification action, `.github`, Gate_SDK, or CI SDK is **not** an implicit remediation. Report the highest owning layer and block only the affected action.
- First scheduled run may occur after the coding campaign. Define `IMPLEMENTED_AND_MANUAL_DEEP_PROVEN` separately from `SCHEDULED_PROOF_PENDING`; this distinction never authorizes skipping a failing manually dispatched deep suite.
- Merge grant is one exact PR/head authorization per merge at the current governance gate. The pack's execution request authorizes bounded PR publication and remediation, not an unspecified merge.
