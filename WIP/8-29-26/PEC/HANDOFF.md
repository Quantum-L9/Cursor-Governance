# PEC handoff — 2026-09-01

Written for whoever picks this up next, including a future session with none of
this context. Read this first, then
[`PEC-repair-pipeline.json`](./PEC-repair-pipeline.json) for the machine state.

**Everything below is verifiable.** Where this brief makes a claim, the command
that proves it is given. Do not trust a status line that has no command beside it.

---

## Where things stand

| | |
|---|---|
| Branch | `claude/cursor-governance-pec-pack-lcw0p8` |
| PR | [#442](https://github.com/Quantum-L9/Cursor-Governance/pull/442) — 17 commits, 48 files, `mergeable: true` |
| Head | `385e2454` |
| CI | 19 success · 2 skipped · 1 failure (not this PR's — see below) |
| Worktree | `/root/cg-pec-wt`, clean |
| Remediation | 17/17 positions complete |
| Findings | 14/14 additive findings closed |
| W0–W7 | complete |
| **W8/S0** | **closed** — gate exits 0 |
| **W8/S1** | **partial** — split closed, U3 closed; three bullets open |
| W8 S2–S8 | unstarted |
| W9, W10 | behind W8 by `depends_on` |

```bash
cd /root/cg-pec-wt
uv run --frozen --no-build python environment/program-execution/scripts/gate_s0_baseline.py   # exit 0
uv run --frozen --no-build python environment/program-execution/scripts/run_conformance.py    # PASS, 659 tests
uv run --frozen --no-build python -m pytest environment/program-execution/tests/hardening -q  # 56 passed, 15 xfailed
```

---

## The one red check is not this PR's

`Analyze (central Core)` fails at *Enforce central mode on SDK technical gate*, on
every head since `b0cee344`. Root cause is in **another repository**:

`l9-ci-sdk` at `7d7762e`, `l9_ci/providers/semgrep/provider.py:396-415` maps **every**
entry of semgrep's `errors[]` to `ProviderFailure(fatal=required)` without reading
the entry's `level`. Semgrep reported `{"level": "warn", "type": "Timeout"}` — a
*warning* — with 669/669 files scanned and all 150 findings produced. Coverage is
derived from that same failures list at `provider.py:431`, so one warning produces
both gate reasons and the gate returns `incomplete` on a bundle with **zero blocking
and zero unresolved findings**.

- Filed: [`l9-ci-sdk#79`](https://github.com/Quantum-L9/l9-ci-sdk/issues/79), [`l9-ci-core#122`](https://github.com/Quantum-L9/l9-ci-core/issues/122)
- Published on the PR: `issuecomment-5486348896`
- Session debt: `sdk-semgrep-warn-promoted-to-fatal`
- **Not re-runnable from this surface** — `rerun-failed-jobs` returns 403.

Nothing in this repository can fix it. It was **not** worked around by excluding the
file or the rule; that would be weakening a security check to force a pass.

---

## The pattern worth carrying forward

Three defects closed this session were **the same defect**:

| Where | What it claimed | What it had checked |
|---|---|---|
| B6 — `worker_validation_claim` | PASS | nothing: both sides of its equality were empty and `all([])` is `True` |
| S1 — `do_not_build` path glob | PASS | nothing: a natural-language law was matched against file paths |
| U3 — `do_not_build` coverage | PASS | only the paths, while saying nothing about the laws it skipped |

**A gate reporting PASS about work it did not do.** If a fourth turns up, stop
fixing them one at a time and consider whether gates should be required to declare
their coverage structurally.

The corollary, learned the hard way in S0: **the fix is never to make the gate
unclearable.** `pinned_to_main` was briefly a blocking S0 condition, which no action
available before a merge could satisfy. It is now advisory and binds at promotion
(S8). A gate nobody can clear teaches people to route around it.

---

## What is actually left in S1

Three of four bullets:

1. `CAMPAIGN_SOURCE → SemanticModel → projections → reconstructed semantics`
2. `semantic_diff` empty on a fixture carrying every governing field
3. `GATE-S1-SEMANTIC-CONSERVATION`

There is **no `SemanticModel` implementation in the tree today**. Verify:

```bash
grep -rn "SemanticModel\|semantic_diff" environment/program-execution/ | grep -v _archive
```

That returns exactly one line — `transport_difference_mistaken_for_semantic_difference`
in `campaigns/bounded-replanning-v1/CAMPAIGN_SOURCE.yaml`, a substring match inside an
unrelated risk id, not an implementation. So this is a build, not a repair.

### Recommended order, and why

1. **Land #442 first.** Every later change gets cheaper to review once `main` moves,
   and it turns S0's `pinned_to_main` from a standing advisory into a real pin.
2. **S1 SemanticModel**, on a fresh branch off that `main`.
3. **S2 / S3** — exact identity, claim-scoped evidence admissibility.

### Do not jump to W9

W9's own invariant is *"No graph edge found is not evidence that no graph edge
exists. Unknown coverage is partial/unknown, never `blast_radius=0`."* That is an
**evidence-admissibility** statement, and admissibility is **S3**. An ImpactEngine
(C8) built on the v2 evidence model produces a `blast_radius: 0` meaning *"I didn't
look"* — the same defect class as the table above, in the most expensive possible
place, because a risk number that reads as safety is worse than an obviously red
gate.

C7 (`l9-assurance` protocol) is *technically* startable — PEC has zero
`l9-assurance` integration today — but a protocol written before the thing it
integrates with tends to get rewritten, and it widens work into a second repo while
#442 is unlanded.

---

## If #442 merges

One mechanical step, then S0 is durably pinned:

```bash
cd /root/cg-pec-wt
# set baseline.pinned_to_main to the merge commit
$EDITOR environment/program-execution/conformance/counterexamples/v2-gaps-registry.yaml
uv run --frozen --no-build python environment/program-execution/scripts/gate_s0_baseline.py
PR_REMEDIATE=0 make -C /root/.cursor-governance pr WS=/root/cg-pec-wt
```

The gate already passes without it; this clears the standing advisory.

---

## Open, deliberately

| Id | Question | Why it is open |
|---|---|---|
| `U2` | Does plane A need a physically detached orchestrator checkout, or is the recorded immutable reference enough? | Resolving by assumption would build W8 machinery the S0 plan excluded. Does not block S0. |
| `U3` | *Closed.* | — |
| — | Should re-scoring `acceptance_scorecard` happen? | Its scores date from `450b7d0e`, before any batch ran. Two rows name blockers since closed. Not re-scored because no measurement was taken after execution, and an invented number is worse than a dated one. |

Four items sit on the session-debt ledger awaiting a human — see
`python3 ops/autonomy/session_debt.py status`.

---

## Reading the tracker safely

`published_at_head` in the JSON is a **snapshot**, and it went stale once already: it
sat at `fea124cd`/11 commits while the branch had reached `385e2454`/17, because it
was written on one publish and not refreshed on the next four. **Read `head_sha`
first**; if it does not match the PR's head, distrust the rest of that block and
trust `git` and the GitHub API instead.

`evidence_at_head` is different — it is deliberately frozen W7-completion history and
is annotated as such. Do not "update" it.
