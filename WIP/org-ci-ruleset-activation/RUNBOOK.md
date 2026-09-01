# Quantum-L9 Canonical CI Activation Runbook

**Run ID:** `L9-ORG-CI-RULESET-ACTIVATION`
**Operator:** human org owner — organization `Administration: write` (classic `admin:org`)
**Target:** organization `Quantum-L9`
**Authority:** `l9-ci-core/.l9/org-runtime-contract.yaml` — org rulesets own targeting
and enforcement; Core owns the workflow.

## Objective

Activate the organization required-workflow ruleset that requires

```
Quantum-L9/l9-ci-core/.github/workflows/org-ci.yml
```

on the default branch of every targeted repository.

This procedure does **not** copy CI into consumer repositories and does **not**
create a second CI control plane. `ownership.prohibited` in the same contract
forbids both.

## Canonical identity

There is exactly one canonical organization ruleset:

```
L9 canonical CI required
```

Its lifecycle is:

```
absent  →  evaluate  →  real consumer canary passes  →  active
```

`evaluate` and `active` are **enforcement states of the same ruleset ID**. They are
not two rulesets. Both payloads in this kit carry the identical `.name` and differ
in `.enforcement` only; `apply.sh` refuses to run if that stops being true, because
name drift turns promotion into a second ruleset and leaves the org with an advisory
one and a blocking one that nobody reconciles.

## Phase checklist

| Phase | Gate | Result required | Owner |
|-------|------|-----------------|-------|
| 0 Preconditions | authority + blast radius understood | `orgs/…/rulesets` readable | Human |
| 1 Dry run | `bash selftest.sh` then `MODE=evaluate bash apply.sh` | selftest green; plan printed, nothing written | Human |
| 2 Create EVALUATE | `DRY_RUN=0 MODE=evaluate bash apply.sh` | `RESULT: ADVISORY_VALID` | Human |
| 3 Canary under EVALUATE | real consumer PR | `RESULT: ADVISORY_CANARY_PASS` | Human |
| 4 Promote to ACTIVE | `DRY_RUN=0 MODE=active bash apply.sh` | `RESULT: LIVE_ENFORCING` | Human |
| 5 Effective-enforcement proof | re-check the canary | `RESULT: LIVE_CANARY_PASS` | Human |

**Any phase that does not print its required result is a STOP.** Do not advance.

---

## Phase 0 — Preconditions

Required locally: `gh`, `jq`.

```bash
gh auth status
gh api orgs/Quantum-L9/rulesets >/dev/null
```

If the second command fails, **STOP**. Every organization ruleset endpoint — `GET`
included, not only `POST`/`PUT` — requires organization `Administration: write`, so
that read succeeding *is* the authority proof. `GET /orgs/{org}` is not: it succeeds
for identities that cannot administer a ruleset.

Three identities fail here by design and cannot be worked around:

| Identity | Why |
|---|---|
| Repo-scoped token | HTTP 403 on `orgs/Quantum-L9/*` |
| Governance GitHub App | manifest grants repo contents/pull_requests + org `members: read` only |
| A Claude Code session | repo-scoped by construction |

Plan is **informational**, not a gate:

```bash
gh api orgs/Quantum-L9 --jq '.plan.name // "unknown"'
```

`evaluate` enforcement is documented Enterprise-only (REST: *"`evaluate` — allows
admins to test rules before enforcement (available with GitHub Enterprise only)"*).
The `workflows` rule's own plan gating is **not** stated in prose anywhere in the
docs; it is inferable only from docs versioning metadata
(`data/features/repo-rules-required-workflows.yml`: `ghec: '*'`, `ghes: '>=3.12'`, no
`fpt` entry) and from the rule's absence from the Free/Pro/Team version of the
"Available rules for rulesets" page. Treat that as strong inference, not a quoted
guarantee.

Either way `.plan.name` is not a capability probe. The authoritative capability check
is the `rulesets` read above plus GitHub accepting the payload, so `apply.sh` prints
the plan and does not branch on it — a hard string match on `enterprise` only invents
a false negative.

If the org genuinely lacks the capability, the honest options are to upgrade the plan
or to change `enforcement_mechanism` in `l9-ci-core` to something achievable and update
the claims. **Do not substitute a per-repo copied workflow** — the contract forbids it.

### Blast radius — read before Phase 2

GitHub, on the `workflows` rule:

> Applying this rule will block direct pushes because the ruleset workflows run as
> part of the pull request and merge queue experience.

This ruleset targets `~DEFAULT_BRANCH` across `~ALL` repositories. Once **ACTIVE**,
direct pushes to the default branch of every Quantum-L9 repository are blocked; all
changes must arrive by pull request. That is consistent with the governed model, but
it is an organization-wide behavioural change and it is the reason Phase 3 runs
*before* Phase 4. Confirm no repository in the org depends on direct default-branch
pushes (release bots, generated-artifact commits, mirror syncs) before promoting.

`bypass_actors` is deliberately empty. An exception granted here is an exception to
canonical CI for that actor in every repository.

### Baseline capture

```bash
cd WIP/org-ci-ruleset-activation
mkdir -p evidence

gh api repos/Quantum-L9/l9-ci-core --jq '.id'
gh api repos/Quantum-L9/l9-ci-core/contents/.github/workflows/org-ci.yml --jq '.path'
gh api orgs/Quantum-L9/rulesets > evidence/org-rulesets.before.json
```

Expected repository ID `1285564308`. **STOP** if more than one ruleset named
`L9 canonical CI required` already exists — resolve that first (see Rollback).

---

## Phase 1 — Dry run

Exercise the kit's own decision logic first. `selftest.sh` runs both scripts against
a stubbed GitHub API — no network, no credentials, no mutation — and asserts every
refusal path, including the payload-identity regression:

```bash
bash selftest.sh          # expect: selftest: 31 passed, 0 failed
```

**STOP** on any failure: a kit that will not refuse correctly must not be pointed at
the organization.

```bash
MODE=evaluate bash apply.sh
```

`apply.sh` fails closed before printing a plan if it cannot read the org's rulesets:
a plan computed without the current inventory cannot distinguish CREATE from UPDATE
and would be a guess.

Expected in the plan:

- ruleset name `L9 canonical CI required`, enforcement `evaluate`
- workflow source `Quantum-L9/l9-ci-core` (`1285564308`) `@ refs/heads/main`
- workflow path `.github/workflows/org-ci.yml`
- targets `["~ALL"] @ ["~DEFAULT_BRANCH"]`
- bypass actors `[]`
- create-gating disabled
- existing: `none` (first run) or exactly one canonical ruleset

Any mismatch: **STOP**.

---

## Phase 2 — Create the EVALUATE ruleset

```bash
DRY_RUN=0 MODE=evaluate bash apply.sh
```

This is the **only** phase permitted to create a ruleset. `MODE=active` refuses to
create one; promotion is never a first write.

The resulting ID is recorded to `evidence/ruleset-id` and asserted on every
subsequent run, so a silently-substituted ruleset is caught rather than promoted.

```bash
bash verify.sh --check
```

Required:

```
RESULT: ADVISORY_VALID
```

The ruleset now exists exactly once and is non-blocking. **Do not promote yet.**

---

## Phase 3 — Real consumer canary, while still EVALUATE

GitHub supports running required workflows in Evaluate mode precisely so the rule can
be exercised before it blocks anything. Use that.

Canary: **`Quantum-L9/l9-observability-core`** — a clean baseline (its effective
rulesets are currently empty) and unambiguously a Python project, so SDK capability
detection is not in question.

1. Create a temporary doc-only branch on the canary.
2. Open a trivial pull request against its default branch — **after** the evaluate
   ruleset exists.
3. Do **not** merge it.

A ruleset created after a PR opened does not retroactively run on it. If the PR
predates Phase 2, push another trivial commit or reopen the PR so GitHub evaluates
the new rule.

```bash
bash verify.sh --pr Quantum-L9/l9-observability-core <PR_NUMBER>
```

Required:

```
RESULT: ADVISORY_CANARY_PASS
```

Verification proves all four, not merely that something passed somewhere:

1. the organization ruleset applies to this consumer;
2. canonical CI ran on the PR's **exact head SHA**;
3. the check run came from GitHub Actions;
4. its conclusion is `success`.

Written to `evidence/remote-end-to-end-run.json` with consumer, PR, head SHA, run URL,
conclusion, and the enforcement state at capture.

If the workflow never appears, the repository is not matched by the ruleset conditions.
If it appears and fails — including on SDK capability detection — **STOP. Do not
activate organization-wide blocking enforcement.** Fix the cause, or abandon the run.

---

## Phase 4 — Promote the SAME ruleset to ACTIVE

Only after Phase 3 passed.

```bash
DRY_RUN=0 MODE=active bash apply.sh
```

This **updates the existing evaluate ruleset in place**. The plan line must read
`existing: id <N> (enforcement=evaluate) — will UPDATE in place`, and the ID before and
after promotion must be identical. `apply.sh` asserts that against
`evidence/ruleset-id` and re-checks afterwards that exactly one canonical ruleset
still exists.

```bash
bash verify.sh --check
```

Required:

```
RESULT: LIVE_ENFORCING
```

Verification proves: exactly one canonical ruleset; `enforcement=active`; source
repository ID `1285564308`; workflow `.github/workflows/org-ci.yml` at
`refs/heads/main`; exactly one required workflow; targets `~ALL` @ `~DEFAULT_BRANCH`;
branch creation not gated; bypass list empty.

Captures `evidence/organization-ruleset-live-enforcement.json`.

---

## Phase 5 — Effective-enforcement proof

Re-check the existing canary PR, or push one more trivial commit to it first:

```bash
bash verify.sh --pr Quantum-L9/l9-observability-core <PR_NUMBER>
```

Required:

```
RESULT: LIVE_CANARY_PASS
```

The sanctioned organization CI path is now live. The canary PR may be closed without
merging.

---

## Rollback

Never select the ruleset by prefix or `startswith` — that is how a rollback deletes
the wrong object. Resolve exactly one:

```bash
ID="$(
  gh api orgs/Quantum-L9/rulesets \
    --jq '[.[] | select(.name=="L9 canonical CI required")] |
          if length == 1 then .[0].id
          else error("expected exactly one canonical ruleset")
          end'
)"
```

**Demote to advisory** (keeps the ruleset and its ID):

```bash
ALLOW_DEMOTE=1 DRY_RUN=0 MODE=evaluate bash apply.sh
bash verify.sh --check     # RESULT: ADVISORY_VALID
```

`ALLOW_DEMOTE=1` is mandatory and deliberate: without it, `apply.sh` refuses to turn
live organization-wide enforcement back into advisory by accident.

**Remove entirely:**

```bash
gh api -X DELETE "orgs/Quantum-L9/rulesets/$ID"
bash verify.sh --check     # must now report no canonical ruleset
```

---

## Trigger distinction — read this before debugging a missing run

`l9-ci-core/.github/workflows/org-ci.yml` natively declares `push`, `pull_request`,
and `merge_group`. Its `push` lane is real and is gated at runtime to the repository's
own `default_branch`.

The organization ruleset does not invoke that lane. GitHub:

> Ruleset workflows support using the `pull_request`, `pull_request_target` and
> `merge_group` events. As a result, you must specify one or more of these events in
> the `on:` section of the workflow for the workflow to be run by a ruleset.

and, on the same page:

> Any filters you specify for the supported events are ignored — for example,
> `branches`, `branches-ignore`, `paths`, `types` and so on.

So: **Core supports `push` natively; the required-workflow ruleset never creates a
push execution.** Both statements are true and they are about different mechanisms.
A missing run on a direct push is expected behaviour, not a broken ruleset.

This is also why `do_not_enforce_on_create: true` is load-bearing. GitHub's option is
"Do not require workflows checks on creation" — it allows branch creation regardless
of the check result. Without it, a creation event would wait on a check the ruleset
cannot produce, and repository creation hangs organization-wide. `apply.sh` refuses a
payload without it.

## Root-commit limit

A pull request needs a base branch. At repository birth the only commit is the root
commit, so there is nothing for it to be a PR against; the root commit cannot be
evaluated before it lands, by this mechanism or any other. `l9-repo-template` reflects
this honestly — a newborn stays `PROVISIONAL` and the first real PR earns `BORN`.

## Completion criteria

Activation is complete only when **all** are true:

- exactly one canonical organization ruleset exists;
- evaluate and active used the same ruleset ID;
- a real consumer canary passed **before** promotion;
- enforcement is `active`;
- the ruleset points exclusively at
  `Quantum-L9/l9-ci-core/.github/workflows/org-ci.yml` at `refs/heads/main`;
- the canary repository sees effective organization enforcement;
- the exact canary PR head completed canonical CI successfully;
- `evidence/organization-ruleset-live-enforcement.json` and
  `evidence/remote-end-to-end-run.json` both exist and show success.

Anything less remains unvalidated. Do not flip either claim in
`l9-ci-core/.l9/org-runtime-interface.yaml` from a dry run, a `workflow_dispatch`, or
a run on a different commit — see `evidence/README.md`.

## Follow-up defects in `Quantum-L9/.github` (not blocking this run)

1. `Makefile:61` — `make apply-rulesets` calls `ops/apply-rulesets.sh`, which has
   never existed in any commit. The working script is `scripts/apply-rulesets.sh`.
2. `rulesets/org-required-analysis.json` — unappliable (`repository_id: 0`) and points
   at the retired `l9-analysis.yml`. Replace with this kit's payload, or delete it.
3. `README.md:84` — documents `ops/apply-rulesets.sh` as existing.

This kit is self-contained and deliberately does not route through any of them.
