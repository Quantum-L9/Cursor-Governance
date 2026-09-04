# L9 PR Remediation — Microscope Audit (findings lock)

**Target:** `skills/l9-pr-remediation` and every live seam it needs to run.
**Exact SHA audited:** `7a6c204547db0fcc8bee9fc35c2202326ebf355d` (`main`, merge of #482).
**Audit branch:** `claude/pr-remediation-skill-audit-2h2zib`.
**Date:** 2026-09-04.
**Mode:** MICROSCOPE → RECONSTRUCT → FINDINGS LOCK (this file) → repair.

Operator directives received during the lock and treated as top authority:

1. The remediator must **not** depend on Program Execution, campaigns, or
   campaign admission. It is a straight-line, high-velocity skill.
2. SonarCloud findings **never block merge**, but when they exist the skill
   must **fully resolve them using the API key** every time it is invoked.

## 1. Executive verdict

The pack is structurally sound on its two hard authorities — the PR board
(`ops/autonomy/pr_board.py`) and the stack-safe merge executor
(`ops/autonomy/stack_safe_merge.py` behind `ops/autonomy/merge_gate.py`) —
and every one of those links resolves and is tested. What is broken is the
**execution model between preflight and merge**:

- Fleet inventory, overlap, stack topology, merge order and the run contract are
  computed by hand from prose, one `gh` call per PR, and re-derived at merge time.
- Parallel remediation exists only as an optional sentence. The only concrete
  launch instruction (`L9_ADMISSION_TOKEN` from `mint_admission.py`) is
  **unreachable**: it requires a bootstrapped root-autonomy campaign with a READY
  action and a Cursor deployment receipt, and nothing compiles a PR fleet into
  one. Per directive 1 it must not.
- Subagent results have **no executable acceptance path** in the skill. The
  canonical validator (`result_bridge.validate_result_against_assignment`) and
  gateway exist and are tested, but the skill never calls them, so a narrative
  "done" is the de facto completion artifact.
- Four references contradict the SKILL contract on the verify/publish verbs and
  on how the issue-remediation handoff is launched.
- SonarCloud is lazy (only when the check is failing) and the fetcher refuses an
  environment-supplied token on every model surface, which directly conflicts
  with directive 2.

No P0 authority or safety defect was confirmed: merge authority, board authority,
stack safety, force-push/admin denial, and the ownership/board axis split all
hold on the audited SHA.

## 2. Complete target skill inventory (26 files, all read in full)

| File | Role | Reachable from hot path | Notes |
|---|---|---|---|
| `SKILL.md` (v4.6.0) | entrypoint | — | 28.5 KB; Defaults YAML duplicates convergence-loop Configuration |
| `agents/meta.yaml` | adapter display | n/a | fine |
| `references/run-contract.md` | preflight/RUN_CONTRACT | yes | P_prs/P_stack/P_board hand-computed |
| `references/diagnose-workflow.md` | Diagnose | yes | fine |
| `references/remediation-plan.md` | per-PR ledger | yes | fine |
| `references/finding-classifier.md` | edit axis + severity | yes | fine |
| `references/fix-engine.md` | fix batch | yes | **contradiction** L53-67 ("public gate is `pr-check`"), **dead wiring** L31-34 (admission token) |
| `references/convergence-loop.md` | post-publish | yes | foreground 15 s polling; duplicated Configuration |
| `references/ownership-boundary.md` | edit axis | yes | fine |
| `references/merge-advise.md` | merge | yes | **contradiction** L589 ("Forbidden: raw `git push` when Makefile `pr` exists") |
| `references/issue-handoff.md` | above-paygrade | yes | **contradiction**: launch as `generalPurpose` vs fix-engine "never generic" |
| `references/code-review-agents.md` | CRA class | yes | fine |
| `references/generated-heal.md` | regen | yes | fine |
| `references/review-angles.md` | Diagnose lenses | optional | fine |
| `references/review-replies.md` | replies | yes | fine |
| `references/signal-ingestion.md` | ingest | yes | completeness list still names `pr-check` / `pr` as PUBLIC verbs |
| `references/validation-gates.md` | gate artifacts | yes | duplicates plan gate; keep as artifact contract |
| `references/sonarcloud-remediation.md` | Sonar signal | lazy | must become always-on when configured (directive 2) |
| `references/codeql-remediation.md` | CodeQL signal | lazy | no `L9_META`; final verdict says "PR **not merged**" (pre-v4 wording) |
| `references/debt-remediation.md` | debt signal | lazy | no `L9_META`; same stale verdict wording |
| `scripts/self_test.py` | pack contract test | validation | reads archived `commands/l9-pr-remediation.md` path (dead); string checks only |
| `scripts/reply_threads.py` | GraphQL batch replies | yes | sound; stdlib |
| `scripts/debt_audit.py` | debt baseline | lazy | sound |
| `scripts/codeql_fetch.py` | CodeQL snapshot | lazy | reads `GITHUB_TOKEN`/`GH_TOKEN` from env on any surface |
| `scripts/sonar_fetch.py` | Sonar snapshot | lazy | **refuses** env `SONAR_TOKEN` on model surfaces (inconsistent with its sibling) |
| `scripts/fixtures/census_graphql.json` | fixture | **unreferenced** | only WIP prune lists name it; dead |

## 3. Reconstructed execution model (current, v4.6.0)

```text
activation ─ Diagnose (read-only) | Converge (/l9-pr-remediation, fix/remediate/babysit/merge)
Converge:
  0 authorize_merge.py --all-open  → ~/.l9/autonomy/merge-authorization.json   [executable, tested]
    RUN_CONTRACT: cache verbs, venv fingerprint, gh pr list, subscribe each PR
    (gh_subscribe_pr.sh), gh pr view --json files ×N, stack probe ×N,
    pr_board.py ×N                                                        [prose-driven, serial]
  1 discover gates (read-only)                                           [prose]
  2 per PR: ingest CI + threads + CRA (+ lazy Sonar/CodeQL/debt)          [prose, serial per PR]
  3 classify (edit axis) + plan ledger                                    [prose]
  4 fix batch ("independent clusters in parallel" — optional, launch via
    mint_admission.py admission token)                                    [UNREACHABLE without a campaign]
  5 L9_REMEDIATOR=1 PR_BASE=origin/main make precommit-repo               [executable]
  6 one commit, git push                                                  [executable; git_guardrails by effect]
  7 reply_threads.py                                                      [executable]
  8 next PR; then own the wait: poll every 15 s ×32 in the foreground     [main agent idle]
  9 MERGE_TRAIN: pr_board.py per head, thread re-query, stack probe,
    stack_safe_merge.py --run (REST then gh; method chosen in code)       [executable, tested]
done: open_prs=0; leftover only with --human-decision/--unfixable-check
      + gh issue create + l9-issue-remediation launch                     [handoff prose]
```

## 4. Autonomy authority map (verified on SHA)

| Concern | Owner | Consumed by skill | Status |
|---|---|---|---|
| Merge authorization receipt | `ops/autonomy/authorize_merge.py` → `merge_gate.py` | yes (Hot Path 0, merge-advise) | wired, tested (`tests/ops/autonomy/test_authorize_merge.py`, `test_merge_gate.py`) |
| Board verdict | `ops/autonomy/pr_board.py` (branch protection ∪ rulesets ∪ required workflows; conflicted paths; unknown→WAIT) | yes | wired, tested |
| Merge execution + stack safety | `ops/autonomy/stack_safe_merge.py` + `merge_gate.py` (`ANCESTRY_BREAKING`, REST + CLI transports) | yes | wired, tested |
| Publish path | `git push` of the open PR branch; `make pr` denied under `L9_REMEDIATOR` (`local_execution_gate.py` L300-448) | yes | wired |
| Destructive git | `ops/autonomy/git_guardrails.py` via `local_execution_gate.py` | implicit | wired |
| Surface doctrine | `ops/autonomy/surface_profile.yaml` (`remediation:` block, `remediator_git_push_of_open_pr`) | discovery pointer in `environment/contracts/autonomy/MANIFEST.yaml` | wired |
| Concurrency caps | `ops/autonomy/claude-execution-profiles.json` via `ops/autonomy/execution_profile.py` (cursor 4/2, claude 480/128) | **not consumed** — caps restated as prose in `l9-bounded-autonomy` | gap (F8) |
| Campaign admission / leases / claims registry | `autonomy/` runtime (`mint_admission.py`, `host_bridge.py`, `scheduler.py`, `claims.py`) | named in fix-engine.md | **not reachable for a PR fleet; excluded by directive 1** |
| Program state | `environment/program-execution/` | none | correct: skill owns no program state |

`environment/contracts/autonomy/MANIFEST.yaml` lists the skill as a consumer of
`autonomy-surface-profile`, `l4-local-autonomy`, and
`context-sensitive-git-guardrails`, and as a `discovery_pointer` projection.
No skill-local surface profile, lease model, or scheduler exists. Good.

## 5. Subagent utilization map

Canonical role set (`environment/agents/cursor-subagents/CURSOR_SUBAGENT_ROLES.yaml`,
mirrored by `result_bridge.AUTONOMY_ROLE_TO_CURSOR_ROLE` and enforced by
`autonomy/tests/test_cursor_role_conformance.py`): `recon`, `pr_remediation`,
`test`, `documentation`, `verifier_reviewer`. Managed task types:
`l9-recon`, `l9-pr-remediation`, `l9-test`, `l9-documentation`,
`l9-verifier-reviewer` (`autonomy/adapters/cursor/adapter.py`).

| Edge | Owner | Skill today |
|---|---|---|
| ready-action identification | none for a PR fleet | prose ("independent PRs may run in parallel") |
| delegation packet (campaign/graph/action/agent/lease/base_sha/role/objective/allowed/forbidden) | `DELEGATION_CONTRACT.yaml` `delegation.input.required` | not produced |
| admission | `mint_admission.py` → root lease | named, unreachable (needs campaign + deployment receipt) |
| role mapping | `result_bridge.canonical_cursor_role` | not used |
| writable scope | assignment `allowed_paths` (capability_gateway grammar) | not produced |
| result document | `schemas/cursor-subagent-result.schema.json` | not required by skill |
| acceptance | `result_bridge.validate_result_against_assignment` / `environment/agents/results/gateway.py` | never called |
| verifier separation | `subject_agent_id` ≠ producer | not expressed |
| above-paygrade handoff | `DELEGATION_CONTRACT.above_paygrade_handoff` | prose, contradictory launch type |

Utilization of the existing module by the skill on the audited SHA: **zero
executable edges**.

## 6. Result flow (canonical, exists, unused by the skill)

```text
Task returns document → validate_result_document (schema)
  → validate_result_against_assignment (identity, role, allowed/forbidden/action paths,
    recon/reviewer no-changes, self-review) → gateway.accept (host status, optional
    root-lease check, correlation, durable acceptance receipt under ~/.l9/agents/results)
  → to_generated_data_packet (partial/blocked/failed never promoted)
```

## 7. Concurrency model and current bottlenecks (serialization classification)

| Point | Today | Class |
|---|---|---|
| `gh pr view --json files` per PR at preflight | serial, hand-run | ACCIDENTAL_SERIALIZATION |
| stack probe per PR (again at merge) | serial, repeated | DUPLICATE_WORK |
| `pr_board.py` per PR | serial | ACCIDENTAL_SERIALIZATION |
| subscribe per PR | serial | ACCIDENTAL_SERIALIZATION |
| per-PR ingest → plan → fix → verify → publish | one PR at a time; parallel optional | ACCIDENTAL_SERIALIZATION (prose), REQUIRED_DEPENDENCY only when files overlap |
| CI wait after publish (15 s × 32 in foreground) | main agent idle up to 8 min per PR | MAIN_AGENT_IDLE_WAIT |
| merge train | oldest-first, one at a time | MERGE_ORDER_REQUIREMENT (correct) |
| Sonar/CodeQL/debt fetch | lazy; serial | EXTERNAL_WAIT; Sonar policy changes under directive 2 |
| lane caps (4/2 vs 480/128) | restated in prose per skill | CURRENT_CONCURRENCY_LIMIT, owner not consumed |

## 8. Duplicate or stale doctrine

- `SKILL.md` Defaults YAML ≡ `convergence-loop.md` Configuration (poll interval, snapshots, cycles, flags).
- `validation-gates.md` Gate B ≡ `remediation-plan.md` plan gate (kept as artifact contract, trimmed).
- `fix-engine.md` Gate Discovery block is the pre-v4 `pr-check` doctrine.
- `merge-advise.md` "raw `git push` forbidden" is the campaign doctrine pasted into the remediator.
- `codeql-remediation.md` / `debt-remediation.md` end with "PR **not merged**" (pre-merge-train).
- Concurrency caps restated in `l9-bounded-autonomy` (4/2) instead of consumed from `execution_profile.py`.

## 9. Dead or partial wiring

- `scripts/fixtures/census_graphql.json`: no consumer.
- `self_test.py` reads `commands/l9-pr-remediation.md`; the command lives only in `commands/_archived/`.
- `fix-engine.md` admission-token launch: no producer for a PR fleet; excluded by directive 1.
- `issue-handoff.md` launch type `generalPurpose` vs `DELEGATION_CONTRACT.above_paygrade_handoff.launch_as: generalPurpose` vs `fix-engine.md` "do not spawn generic generalPurpose": the contract says the handoff is the specialised issue skill run as a `generalPurpose` Task under the `pr_remediation` role rules; the pack states it three different ways.

## 10. Findings register

Severity: P0 authority/safety · P1 runtime/skill correctness · P2 concurrency/wiring · P3 non-blocking debt.

### P0

None confirmed. Board, merge, stack-safety, publish-path, and destructive-git
authority all resolve to their canonical owners on the audited SHA and are
covered by executable tests.

### P1

| Id | Category | Owner / paths | Current | Expected | Root cause | Serialization / underutilization | Smallest authoritative fix | Validation |
|---|---|---|---|---|---|---|---|---|
| F1 | DEAD_WIRING / SUBAGENT_WIRING | `references/fix-engine.md` L31-34; `environment/agents/cursor-subagents/README.md` lifecycle | parallel launch requires `L9_ADMISSION_TOKEN` from `mint_admission.py`, which needs a bootstrapped campaign + READY action + Cursor deployment receipt | a launchable wave for a plain PR fleet without campaigns | admission path was written for campaigns; no fleet→graph producer; directive 1 forbids adding one | yes / yes | deterministic fleet planner (`ops/autonomy/pr_fleet.py`) emits bounded assignments per `DELEGATION_CONTRACT.delegation.input`; skill launches native Tasks from them; drop the admission instruction | `tests/ops/autonomy/test_pr_fleet.py`, `self_test.py` |
| F2 | RESULT_CONTRACT / VERIFICATION | `SKILL.md` Hot Path 4, 8; `result_bridge.py`; `results/gateway.py` | subagent "done" accepted by prose; validator and gateway never called | every returned document validated against its assignment; partial/blocked/failed preserved; recon with changed files rejected | skill never wired the existing result contract | no / yes | `pr_fleet.py accept` calls `validate_result_against_assignment` and `gateway.accept` | fleet tests: wrong base SHA, wrong role, outside allowed paths, recon changes, partial preserved |
| F3 | CONCURRENCY / DUPLICATE_WORK | `run-contract.md` P_prs/P_stack/P_board; `SKILL.md` Hot Path 0, 9 | inventory, files, stack, board, subscribe run one PR at a time by hand; stack probed again at merge | one inventory pass, parallel REST, receipt with fingerprint, merge order computed | no executable owner | yes / yes | `pr_fleet.py plan` (parallel REST fetch, topology, merge order, boards, receipt `.l9/pr/fleet.json`) | fleet tests + velocity model |
| F4 | SKILL_CONTRACT (contradictions) | `fix-engine.md` L53-72, L189; `merge-advise.md` L589-590; `signal-ingestion.md` L575-576; `issue-handoff.md` L652 | verify = `pr-check` / publish must not be raw `git push` / PUBLIC verbs `pr-check`,`pr` / handoff launch as generic | verify = `make precommit-repo`, publish = `git push`, handoff = specialised issue skill as a `generalPurpose` Task under `pr_remediation` role rules | pre-v4 text left in place | no / no | rewrite those blocks; `self_test.py` forbids the stale strings | `self_test.py`, `tests/ops/scripts/test_ceremony_ownership.py` |
| F5 | AUTHORITY (directive 2) / DEAD_WIRING | `scripts/sonar_fetch.py` `build_transport`, `DirectTransport.__init__`; `SKILL.md` Converge table; `sonarcloud-remediation.md` | Sonar fetched only when its check is failing; token refused on any model surface even when the operator environment supplies it (sibling `codeql_fetch.py` reads `GITHUB_TOKEN` from env) | when `sonar-project.properties` exists, fetch authenticated with the env token on every Converge, resolve every confirmed issue on the PR head, never block merge on it, claim remote closure only when observed | fetcher conflated "ops/secrets must not export a secret" with "a token already in the process env may not be used" | no / no | use env `SONAR_TOKEN`/`SONARCLOUD_TOKEN` when present, any surface; never print or store; ops/secrets export boundary unchanged | `tests/ops/secrets/test_capability_plane.py` §13 updated |
| F6 | TEST_GAP / STALE_REFERENCE | `scripts/self_test.py` | reads archived command path; string-presence only; no wiring or concurrency coverage | validates the live contract incl. fleet wiring | grew by accretion | no / no | rewrite `self_test.py` around the v5 contract | run it |

### P2

| Id | Category | Owner / paths | Current | Expected | Fix |
|---|---|---|---|---|---|
| F7 | SERIALIZATION / POLLING | `SKILL.md` Law 8, Hot Path 8; `convergence-loop.md` | foreground 15 s polling, ≤32 snapshots, one PR at a time | watcher wave in the background (read-only `recon` role); main agent continues the next ready PR or the merge-train preflight | wave model in `pr_fleet.py`; SKILL Hot Path rewritten |
| F8 | DUPLICATED_DOCTRINE (caps) | `l9-bounded-autonomy/references/parallel-nondependent.md`, `doctrine-map.md`; `SKILL.md` | caps restated in prose | caps read from `execution_profile.py` (cursor 4/2, claude 480/128) | `pr_fleet.py waves` consumes the profile; skill cites the owner, no numbers in prose |
| F9 | DEAD_WIRING | `scripts/fixtures/census_graphql.json` | unreferenced | removed; fleet probe fixtures live in tests | delete |
| F10 | DUPLICATED_DOCTRINE | `SKILL.md` Defaults ↔ `convergence-loop.md` Configuration | two copies | one owner (SKILL.md Defaults) | remove the copy |
| F11 | STALE_REFERENCE | `codeql-remediation.md`, `debt-remediation.md` | no `L9_META`; "PR **not merged**" verdicts | `L9_META`; verdict hands the PR to the merge train | edit |

### P3

| Id | Category | Note |
|---|---|---|
| F12 | INFORMATIONAL | At lock time `validate_exemplary_skill.py` reported missing `expertise_model.yaml` / `skill_intelligence_report.yaml` (pack tier `strong`). Closed after the findings lock on operator request ("make it exemplary"): both artifacts plus `scripts/activation_cases.json` added at 5.1.0; the validator passes. Activation precision is measured by `self_test.py`, not asserted. |
| F13 | RESULT_CONTRACT | Result identity fields assume campaign/lease vocabulary. For a non-campaign bounded task the ids are run-scoped correlation keys (`lease_id = no-root-lease-<assignment>`); the gateway checks a root lease only when a runtime database is named, so nothing is faked. Documented in `pr_fleet.py`; contract unchanged. |
| F14 | INFORMATIONAL | `reviewThreads` is GraphQL-only; on a GraphQL-restricted surface `pr_board.py` degrades honestly (threads `None`, board never MERGE on unknown). `pr_fleet.py` is REST-only by design. |

## 11. Root-cause clusters

| Cluster | Findings | Repair owner |
|---|---|---|
| C1 no deterministic fleet owner | F1, F2, F3, F7, F8 | `ops/autonomy/pr_fleet.py` + tests |
| C2 pre-v4 prose left in references | F4, F10, F11 | pack references |
| C3 Sonar policy vs directive 2 | F5 | `sonar_fetch.py`, SKILL Converge table, `sonarcloud-remediation.md`, capability tests |
| C4 pack test debt | F6, F9 | `self_test.py`, fixture removal |

## 12. Repair order

1. C1 — build `pr_fleet.py` and its tests (nothing else can be validated without the owner).
2. C3 — `sonar_fetch.py` env token; tests; contract rows.
3. C2 + C4 — SKILL.md v5.0.0 and references; `self_test.py`; drop fixture.
4. Regenerate the skill registry (companion of a SKILL.md description/version change).
5. Validators: `validate_skill_pack.py`, `self_test.py`, targeted pytest, ruff, `validate_autonomy_contracts.py`.
6. Final microscope on every changed file; hardening brief.

## 13. Files that must not be edited

`ops/autonomy/pr_board.py`, `stack_safe_merge.py`, `merge_gate.py`,
`authorize_merge.py`, `surface_profile.yaml`, `environment/contracts/autonomy/**`,
`environment/agents/cursor-subagents/**`, `environment/agents/results/**`,
`autonomy/**`, `rules/**`, generated registries by hand.

## 14. No-fix findings

F12, F13, F14 (see P3).

## 15. Unresolved UNKNOWNs

- Whether `SONAR_TOKEN` is present in a given operator session is environment
  state; absent in this audit container. The repaired fetcher reports
  `authenticated: false` honestly when it is absent.
- Live GraphQL availability on a given surface (affects `reviewThreads` and
  `gh pr` subcommands); both helpers already degrade to REST or to WAIT.
