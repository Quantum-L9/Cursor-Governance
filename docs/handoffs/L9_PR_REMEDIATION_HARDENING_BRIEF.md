# L9 PR Remediation — Hardening Brief

**Executive verdict:** `L9_PR_REMEDIATION_HARDENED_ALIGNED_AND_CONCURRENCY_IMPROVED`
(pending publication state; see §16).

**Initial SHA:** `7a6c204547db0fcc8bee9fc35c2202326ebf355d` (`main`).
**Candidate:** branch `claude/pr-remediation-skill-audit-2h2zib` (final SHA in the PR).
**Findings lock:** `docs/handoffs/L9_PR_REMEDIATION_MICROSCOPE_AUDIT.md`.

Operator directives honoured: (1) no Program Execution / campaign / admission
dependency — the skill is a straight line; (2) SonarCloud findings never block
merge but are fully resolved with the API key whenever they exist.

## 1. Microscope scope and files read

All 26 files of `skills/l9-pr-remediation` in full, plus every material seam:
`environment/contracts/autonomy/{MANIFEST.yaml,README.md}`,
`ops/autonomy/{surface_profile.yaml,pr_board.py,stack_safe_merge.py,authorize_merge.py,merge_gate.py,local_execution_gate.py (remediator section),execution_profile.py,claude-execution-profiles.json}`,
`environment/agents/cursor-subagents/{README.md,CURSOR_SUBAGENT_ROLES.yaml,DELEGATION_CONTRACT.yaml,result_bridge.py,schemas/*}`,
`environment/agents/results/{RESULT_CONTRACT.yaml,adapters/cursor_subagent.py,gateway.py,receipts.py}`,
`environment/agents/lifecycle/{receipts.py,schemas.py,compose_start.py}`,
`environment/agents/runtime_paths.py`, `environment/agents/PEER_EXECUTION.md`,
`rules/77-cursor-subagent-orchestration.mdc`,
`autonomy/{README.md,adapters/cursor/*,adapters/orchestrator.py,adapters/conformance.py,adapters/contract_renderer.py,compiler/graph_compiler.py,runtime/{scheduler,claims,leases,capability_gateway,artifacts,engine}.py,validation/graph_linter.py,policies/*.json,examples/*}`,
`skills/l9-bounded-autonomy/{SKILL.md,references/*}`, `skills/l9-issue-remediation/{SKILL.md,references/handoff-to-pr-remediation.md}`,
`skills/l9-skill-compiler/{SKILL.md,references/skill-pack-contract.md,references/meta-standard.md}`, `skills/l9-wire-into-repo/SKILL.md`,
`ops/secrets/{surface_trust.py,capabilities.yaml,RETIRED.md}`, `docs/DEGRADED_MODE_CONTRACT.md`,
`ops/scripts/lib/gh_subscribe_pr.sh`, `commands/{pr,issues,pr-train}.md`, `Makefile` (remediator targets),
and the tests around each owner.

## 2. Architecture reconstructed (after)

```text
/l9-pr-remediation Converge
  authorize_merge.py --all-open                         (merge receipt; merge_gate.py consumes)
  pr_fleet.py plan --board                              (ONE REST pass, parallel files + boards;
                                                         stack edges, overlap, merge_order, waves,
                                                         fingerprint → .l9/pr/fleet.json)
  pr_fleet.py assign --kind remediate|recon|watch       (bounded assignment per PR:
                                                         DELEGATION_CONTRACT inputs, allowed/forbidden
                                                         paths, managed Task type, prompt)
  ONE message: launch every lane in waves.first_wave    (caps from execution_profile.py)
  each lane: diagnose → plan → fix (Sonar included) → L9_REMEDIATOR=1 make precommit-repo
             → one commit → git push → reply_threads.py → result document
  pr_fleet.py accept                                    (result_bridge.validate_result_against_assignment
                                                         + results gateway receipt; partial/blocked preserved)
  next wave until REMEDIATE_ALL; watchers own CI waits in the background
  MERGE_TRAIN over merge_order: pr_board.py per head → stack_safe_merge.py --run
```

Owners unchanged: board (`pr_board.py`), merge (`stack_safe_merge.py` + `merge_gate.py`),
authorization (`authorize_merge.py`), caps (`execution_profile.py`), roles and result
contract (`cursor-subagents`, `results`). Nothing new owns program state, leases, or
scheduling.

## 3. Defects found and root causes fixed

| Id | Finding | Fix |
|---|---|---|
| F1 | parallel launch depended on an unreachable campaign admission token | `pr_fleet.py assign`; admission instruction removed from `fix-engine.md` |
| F2 | no executable result acceptance; narrative "done" was completion | `pr_fleet.py accept` → canonical bridge + gateway; Law 9 |
| F3 | fleet/overlap/stack/merge-order computed by hand, serially, twice | `pr_fleet.py plan` (parallel REST, fingerprint receipt) |
| F4 | four references contradicted the verify/publish verbs and the handoff launch | `fix-engine.md`, `merge-advise.md`, `signal-ingestion.md`, `issue-handoff.md` repaired; `self_test.py` forbids the stale strings |
| F5 | Sonar lazy and token refused on model surfaces (directive 2) | `sonar_fetch.py` uses an env-supplied token on any surface, never exports/prints; SKILL Law 13, `sonarcloud-remediation.md` "When (always, never blocking)"; capability tests §13 rewritten |
| F6 | `self_test.py` read an archived command path; string-only | rewritten around the v5 contract (links, owners, no second plane, waves, Sonar) |
| F7 | foreground 15 s polling idled the main agent | watcher lane (`--kind watch`, read-only `recon`); `convergence-loop.md` |
| F8 | caps restated as prose | `pr_fleet.py profile_caps` reads `execution_profile.py`; pack states no number (enforced by `self_test.py`) |
| F9 | dead fixture `scripts/fixtures/census_graphql.json` | deleted |
| F10 | Defaults duplicated in `convergence-loop.md` | single owner (SKILL.md) |
| F11 | `codeql-remediation.md` / `debt-remediation.md`: no `L9_META`, "PR not merged" verdicts | `L9_META` added; verdicts hand to MERGE_TRAIN |

## 4. Target skill changes

- `SKILL.md` 4.6.0 → 5.0.0 → 5.1.0 (`tier: exemplary`; intelligence layer + after-use capture): deterministic-owners table; Laws rewritten
  (fleet plan, one-message wave, results-as-documents, watcher-owned waits, Sonar
  resolve-fully/block-never); Hot Path 0–10 on `pr_fleet.py`; Defaults gain
  `fleet_owner`, `replan_on`, `wave_launch`, `concurrency_caps_owner`,
  `result_acceptance`, `watcher_role`, `sonarcloud`.
- New `references/fleet-waves.md` (wave shapes, launch, accept, next wave, never-list).
- `run-contract.md` P_prs/P_stack → `P_fleet`; command surface + RUN_CONTRACT schema carry the fleet receipt.
- `fix-engine.md`, `merge-advise.md`, `issue-handoff.md`, `signal-ingestion.md`,
  `convergence-loop.md`, `sonarcloud-remediation.md`, `codeql-remediation.md`,
  `debt-remediation.md`, `agents/meta.yaml` repaired as in §3.
- `scripts/self_test.py` rewritten; `scripts/sonar_fetch.py` token path repaired;
  `scripts/fixtures/` removed.

## 5. Autonomy wiring changes

None to the autonomy plane itself. The skill now consumes `execution_profile.py`
(caps), `autonomy.runtime.claims.claim_scopes_conflict` (conflict primitive) and
`sync_generated_artifacts.is_generated_path` through `pr_fleet.py`. No campaign,
lease, admission, or scheduler was added or touched. `validate_autonomy_contracts.py`
PASS.

## 6. Subagent wiring changes

The skill now produces `DELEGATION_CONTRACT.delegation.input`-shaped assignments
and judges every returned `l9.cursor-subagent.result.v1` document through the
canonical bridge and gateway. Managed Task types and background policy come from
`CURSOR_SUBAGENT_ROLES.yaml` via the adapter. No contract file was edited; no
sixth role exists; watchers are the read-only `recon` role.

Identity note (F13 in the audit): for a non-campaign task the assignment's
`lease_id` is `no-root-lease-<assignment_id>`, a correlation key. The gateway
checks a root lease only when a runtime database is named, so nothing is faked.

## 7. Concurrency and velocity changes

- Inventory once; per-PR files and boards fetched concurrently (8 workers).
- Mutation wave = maximal claim-conflict-free set under the profile cap;
  generated-only overlap never serializes; stacked children mutate concurrently
  with parents and merge after them.
- Recon and watch lanes fill the read budget of the same wave.
- Fingerprint (`number`, head SHA) reuses the plan until a head moves.

## 8. Deterministic components changed

- New: `ops/autonomy/pr_fleet.py` (plan / waves / assign / accept / model).
- Changed: `skills/l9-pr-remediation/scripts/sonar_fetch.py`, `scripts/self_test.py`.
- Regenerated companions: `ops/generated/skill-registry.json`,
  `environment/agents/adapters/claude-code/generated/skill-registry.json`.

## 9. Tests added or changed

- New `tests/ops/autonomy/test_pr_fleet.py` (20 cases): caps owner; independent /
  overlap / generated-only / stacked / cap-deferred / waiting fleets; fingerprint
  reuse and invalidation; fail-closed on missing head; assignment contract inputs;
  acceptance (correct, stale base SHA, wrong lease/action/role, outside grant,
  forbidden path, recon with changes, partial preserved, narrative rejected,
  gateway receipt + host-status override); velocity model; CLI round trip.
- `tests/ops/secrets/test_capability_plane.py` §13: env token used on a model surface
  without leaking; unauthenticated when absent; secret-plane export still denied.
- `scripts/self_test.py` rewritten (structural + wiring).

## 10. Before/after velocity evidence (deterministic counts, not timings)

`pr_fleet.py model` on a six-PR fixture (2 independent, 2 generated-only overlap,
1 stacked pair). "Serial" is a model of the v4.6 prose hot path.

| Counter | serial (v4.6) | waves, Claude surface | waves, Cursor surface |
|---|---|---|---|
| remote queries at preflight | 13 | 7 (2 rounds) | 7 (2 rounds) |
| duplicate stack probes at merge | 6 | 0 | 0 |
| first wave launched / parallelism | 1 / 1 | 6 / 6 | 4 / 4 (2 mutators, 2 recon; 4 deferred by the 2-lane cap) |
| main-agent foreground waits | 6 (≤192 poll snapshots) | 0 | 0 |
| mutation waves | 6 | 1 | 3 |

Overlap fixture (PR 2 shares `ops/shared.py` with PR 1; PR 3 independent):
first wave `remediate=[1,3]`, `recon=[2]`, `blocked_claim=[{pr:2, conflicts_with:[1]}]`,
second wave `remediate=[2]` — conflicting mutation is serialized, nothing else is.

Collision count in every fixture: 0 conflicting mutators admitted to one wave
(asserted by the tests). Correctness regressions: none (742 tests in the affected
suites pass). Resource-limit changes: none; caps are read from their owner.

## 11. Skill validation (executed)

| Check | Result |
|---|---|
| `skills/l9-skill-compiler/scripts/validate_skill_pack.py skills/l9-pr-remediation` | PASS (29 files) |
| `skills/l9-pr-remediation/scripts/self_test.py` | PASS (incl. activation precision over `scripts/activation_cases.json`: 18 labeled prompts, 0 wrong activations) |
| `skills/l9-skill-compiler/scripts/validate_exemplary_skill.py skills/l9-pr-remediation` | PASS (`expertise_model.yaml` + `skill_intelligence_report.yaml`, all ten gates `pass`, tier `exemplary`) |
| `ruff check` + `ruff format --check` on changed Python | PASS |

## 12. Autonomy validation (executed)

`ops/scripts/validate_autonomy_contracts.py` PASS; `tests/ops/autonomy` (incl.
`test_pr_board.py`, `test_stack_safe_merge.py`, `test_merge_gate.py`,
`test_authorize_merge.py`, `test_pr_fleet.py`) PASS.

## 13. Subagent validation (executed)

`environment/agents/cursor-subagents/tests`, `environment/agents/results/tests`,
`autonomy/tests/test_cursor_result_contract.py`, `test_cursor_role_conformance.py`,
`test_claim_overlap.py`, `environment/agents/tools/validate_agents.py` — all PASS.
Combined affected run: **742 passed**.

## 14. Final microscope result

Every changed file re-read on the candidate: no new authority owner, no shadow
scheduler, no role registry, no lane number in prose, no generated file
hand-edited (registries regenerated by `sync_generated_artifacts.py`), no
path-collision path (conflict primitive is canonical), no weakened gate (secret
export still denied; export test added), no false completion path (acceptance
fails closed).

## 15. Remaining non-blocking debt and UNKNOWNs

- Pack tier is `exemplary` (5.1.0). The intelligence layer is two YAML artifacts plus one labeled-prompt fixture; the executable owners did not change and no lane number entered prose.
- `pr_fleet.py` is REST-only; `reviewThreads` stays GraphQL-only inside `pr_board.py`, which degrades to `wait` when unavailable.
- `SONAR_TOKEN` was absent in the audit container; the fetcher reports `authenticated: false` in that case and the skill records the gap.
- The velocity table models the shipped prose; a live timed run was not possible here (no open fleet in the container).

## 16. Repository publication state

Recorded in the pull request opened from `claude/pr-remediation-skill-audit-2h2zib`
(base `main`). Merge stays with `/l9-pr-remediation` per repository law.
