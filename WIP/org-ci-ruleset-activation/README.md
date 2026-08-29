# Make the sanctioned CI path live

**Status:** not live. Nothing in Quantum-L9 currently receives canonical CI.

This kit is the missing step. Everything else in the architecture already assumes
it has happened.

---

## The gap, in evidence

`l9-ci-core/.l9/org-runtime-contract.yaml` declares the enforcement surface:

```yaml
entrypoint:
  workflow: .github/workflows/org-ci.yml
  enforcement_mechanism: github_organization_required_workflow_ruleset
  ruleset_events: [pull_request, merge_group]
  consumer_copy_required: false
  consumer_core_pin_allowed: false
```

Nothing has ever applied that ruleset. Verifiable from a repo-scoped token:

```bash
for r in l9-ci-core l9-ci-sdk l9-repo-template l9-observability-core .github; do
  gh api "repos/Quantum-L9/$r/rulesets?includes_parents=true" \
    --jq '[.[] | {name, source_type, enforcement}]'
done
```

Every entry comes back `source_type: "Repository"`. **No organisation ruleset
exists.** `l9-observability-core` — the newest governed repo — returns `[]` and has
zero workflows; its only checks are GitHub's dynamic CodeQL and Dependabot.

Core records the same thing about itself, in
`l9-ci-core/.l9/org-runtime-interface.yaml`:

```yaml
  - id: organization-ruleset-live-enforcement
    evidence: []
    status: UNKNOWN
  - id: remote-end-to-end-run
    evidence: []
    status: UNKNOWN
```

`org-ci.yml` has never executed. No workflow anywhere `uses:` it; `self-analysis.yml`
dogfoods `analyze-semgrep.yml` instead.

---

## Two GitHub constraints that shape everything

**1. Required workflows are an organisation-level ruleset, and never run on `push`.**
GitHub supports `pull_request`, `pull_request_target` and `merge_group` only.

**2. A pull request needs a base branch.** At repository birth the only commit that
exists is the root commit, so there is nothing for it to be a PR against. The root
commit therefore **cannot** be evaluated before it lands, by this mechanism or any
other. That is why `l9-repo-template` leaves a newborn `PROVISIONAL` and lets the
first real PR earn `BORN`, rather than pretending otherwise.

---

## Preconditions

| Requirement | Why | Check |
|---|---|---|
| GitHub **Enterprise Cloud** | the `workflows` ruleset rule is an Enterprise Cloud feature | `gh api orgs/Quantum-L9 --jq .plan.name` |
| `organization_administration: write` (classic `admin:org`) | `POST /orgs/{org}/rulesets` requires it | `gh api orgs/Quantum-L9/rulesets` returns 200 |
| `gh` + `jq` | | |

**The governance GitHub App cannot do this.** Its provisioned manifest grants
repository `contents` / `pull_requests` plus organisation `members: read`. It has no
`organization_administration` permission, and no workflow in `Quantum-L9/.github`
calls `orgs/*/rulesets`. Run this as a human org owner.

A Claude Code session cannot do it either — repo-scoped tokens get HTTP 403 on
`orgs/Quantum-L9/*`. `apply.sh` detects that and says so instead of failing obscurely.

### If the org is not Enterprise Cloud

Then `enforcement_mechanism: github_organization_required_workflow_ruleset` is
**unavailable**, and no tooling changes that. The honest options are:

1. Upgrade the plan.
2. Change the contract in `l9-ci-core` to an achievable mechanism and update the
   claims accordingly.

Do not substitute a per-repo copied workflow: `ownership.prohibited` in the same
contract forbids "copied L9 workflows in consumer repositories as an enforcement
mechanism" and "consumer-owned Core or SDK pins for organization enforcement".

---

## Run it

```bash
cd WIP/org-ci-ruleset-activation

bash apply.sh                              # dry run — prints the plan, changes nothing
DRY_RUN=0 bash apply.sh                    # apply ADVISORY (evaluate) first
bash verify.sh --check                     # confirm the ruleset landed

DRY_RUN=0 MODE=active bash apply.sh        # promote to BLOCKING
bash verify.sh --check
```

Then prove it end-to-end against a real consumer — `l9-observability-core` is the
natural canary (public, currently zero rulesets):

```bash
# open any trivial PR on the canary, then:
bash verify.sh --pr Quantum-L9/l9-observability-core <pr-number>
```

That correlates the check run to the PR's **exact head SHA** — a stale success or a
run on another commit is rejected — and writes `evidence/remote-end-to-end-run.json`.

---

## What the payload fixes

`Quantum-L9/.github/rulesets/org-required-analysis.json` is the only ruleset JSON in
the org and it cannot be applied:

| Defect there | Here |
|---|---|
| `"repository_id": 0` — not a real repository | `1285564308` (`Quantum-L9/l9-ci-core`, verified via `gh api repositories/1285564308`) |
| points at `l9-analysis.yml` — the retired copy-first workflow | `.github/workflows/org-ci.yml` |
| `enforcement: evaluate` only | evaluate **and** active variants |
| no `do_not_enforce_on_create` | `true` — see below |

**`do_not_enforce_on_create: true` is load-bearing.**
`Quantum-L9/.github/rulesets/README.md` warns that gating branch *creation* "can
block repository creation entirely". Since `org-ci.yml` declares no `push` trigger, a
creation-gated check would never resolve and every new repository in the organisation
would hang. `apply.sh` refuses to apply a payload without it.

---

## Known blocker, upstream

`org-ci.yml` lines 288-291:

```python
else:
    raise SystemExit(
        "SDK capability detection is ambiguous; set repo_class in optional .l9/ci.json"
    )
```

This fires when the SDK detects **both** Python and TypeScript **or neither**. A
freshly born repository may well detect neither, so the first canary PR can fail here
rather than on anything this kit controls.

Workaround: add `.l9/ci.json` to the consumer with an explicit `repo_class` (the
schema accepts only `schema`, `owner`, `repo_class`, `waiver_refs`).

Proper fix, in `l9-ci-core`: the `else` branch has no "no languages detected" escape.
That is worth an issue against Core, not a patch here.

---

## Rollback

```bash
ID=$(gh api orgs/Quantum-L9/rulesets --jq '.[] | select(.name | startswith("L9 canonical CI required")) | .id')
gh api -X DELETE "orgs/Quantum-L9/rulesets/$ID"
```

Or demote to advisory by re-running `DRY_RUN=0 bash apply.sh` (evaluate mode).

---

## Optional follow-up in `Quantum-L9/.github`

Not required — this kit is deliberately self-contained — but these are real defects
found while building it:

1. `Makefile:61` — `make apply-rulesets` calls `ops/apply-rulesets.sh`, which **has
   never existed in any commit**. The working script is `scripts/apply-rulesets.sh`.
2. `rulesets/org-required-analysis.json` — unappliable (`repository_id: 0`) and points
   at the retired workflow. Replace with this kit's payload, or delete it.
3. `README.md:84` — documents `ops/apply-rulesets.sh` as existing.
