<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: sonarcloud_signal
tags: [sonarcloud, static-analysis, root-cause, minimal-change, fail-closed]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-04
/L9_META -->

# SonarCloud Remediation Signal

SonarCloud findings are a **third signal source** alongside CI failures and review-bot
comments. They are retrieved from the API, confirmed against current source, collapsed
to root causes, and fixed with the smallest safe change — never chased by suppression.

This signal is **fail-closed** and **read-only against SonarCloud**: never mutate remote
issue state, never weaken analysis, and never claim remote closure from local reasoning.

## Identity binding (preflight)

Resolve and record before any fix:

- `organization`, `project_key` — from `sonar-project.properties` (`sonar.organization`,
  `sonar.projectKey`) or explicit user input. Ambiguous identity → **STOP (BLOCKED)**.
- `branch` or `pullRequest` — remediate only issues on the **exact** target branch/PR
  under test. Never mix findings from unrelated branches.
- `analyzed_revision` and `latest_analysis_date` — compare SonarCloud's analyzed revision
  with local `HEAD`. If they materially differ and cannot be reconciled → **STOP (BLOCKED)**.
- Auth: read `SONAR_TOKEN` **by environment reference only**. Public projects read without
  a token. Never print, commit, or store the token; redact `Authorization` headers.

## Retrieve (fail-closed, paginated)

Use `scripts/sonar_fetch.py` (stdlib, secret-safe) to produce `sonarcloud-issues-before.json`:

```bash
python scripts/sonar_fetch.py \
  --project Quantum-L9_Cursor-Governance --organization quantum-l9 \
  --pull-request 64 --output sonarcloud-issues-before.json
  # --output must stay under $PWD; never /tmp
# branch analysis instead of a PR: --branch main
```

The fetcher paginates `/issues/search` until `total` is reached, resolves distinct
`/rules/show`, and captures `/qualitygates/project_status` + `/measures/component`. It
records request params (credentials redacted), response timestamps, and the pagination
receipt. A partial fetch (`retrieved != total`) is **BLOCKED**, not a smaller issue set.

Status handling: evaluate `OPEN`/`CONFIRMED`/`REOPENED`; preserve+revalidate `ACCEPTED`;
exclude `FALSE_POSITIVE`/`FIXED`/`CLOSED` unless current evidence contradicts.

## Confirm before fix

An issue is a mutation target only after it is confirmed against the current revision:

1. Open the file at the analyzed revision; locate the exact symbol and range.
2. Reproduce the rule condition; read callers, consumers, and related tests.
3. Check repository architecture, contracts, and generated/vendored/excluded scope.
4. Decide validity — `CONFIRMED_DEFECT`, `VALID_BUT_NON_BLOCKING`, `FALSE_POSITIVE_CANDIDATE`,
   `STALE_FINDING`, `GENERATED_OR_VENDOR_SCOPE_ERROR`, or `UNKNOWN`.

Do not modify code solely because SonarCloud reported it. A stale, generated, or
false-positive finding is recorded with evidence and **left unchanged** — remote state is
never mutated to clear it.

## Cluster by root cause, then prioritize

Collapse findings into the smallest set of independent root causes whose correction
removes the most valid issues. Cluster by: same rule+pattern, same function/class, same
shared utility, same data contract, same error-handling / nullability / resource-lifecycle
gap, same security boundary, same generated template, same config defect, same architectural
violation.

Each cluster records: `cluster_id`, `root_cause`, `issue_keys`, `issue_count`,
`affected_files`, `severity_max`, `behavioral_risk`, `proposed_minimal_fix`,
`expected_issue_reduction`, `required_validation`, `confidence`.

Maximize blocker/critical reduction, valid issues closed, shared-cause elimination, and
security/reliability impact. Minimize files changed, semantic surface, compatibility risk,
architectural disruption, and test burden. Fix order: confirmed security vulnerabilities →
confirmed runtime bugs → blocker/critical → shared causes → quality-gate blockers → major
maintainability → low-risk/high-leverage minor/info → disputed/UNKNOWN.

## Minimal-fix contract

Fix the **authoritative owner**, once. Preserve public behavior, API/schema compatibility,
error semantics, security controls, logging/observability, and generated-source authority.
Add no dependency, no unrelated formatting, no broad refactor. Change no more files than the
root cause requires.

**Prohibited shortcuts** (any of these fails the cluster): `NOSONAR`, blanket rule
suppression, broad exclusions, lowering a quality-gate threshold, marking a valid issue
false-positive, deleting tests, weakening assertions, ignoring type errors, replacing logic
with a stub, swallowing exceptions, unsafe non-null assertions, cosmetic no-op changes.

**Suppression** is allowed only when the finding is *proven* a false positive, repo policy
permits it, the rationale is documented adjacent to the code, and a code-level fix would make
the implementation less correct or less safe. (This repo's `sonar-project.properties` already
documents its accepted path-escape exclusions — extend that pattern, never `NOSONAR`.)

## Security hotspots

Hotspots require review-quality evidence. For each: identify the sensitive operation, input
origin, authn/authz, validation/encoding, and secret/logging behavior; classify
`SAFE_REVIEWED` / `CONFIRMED_RISK` / `UNKNOWN`; patch only `CONFIRMED_RISK`. Never auto-edit
safe code to clear a hotspot, and never mutate remote hotspot status.

## Validate — local vs remote are different truths

Run the repository-native gates (install, targeted tests for each fixed cluster, negative
case for each runtime/security fix, lint, type-check, build, and the local Sonar scanner when
the repo supports it and it is safe). Result values: `PASS`, `FAIL`, `BLOCKED`, `UNKNOWN`,
`PENDING_REMOTE_ANALYSIS`.

- `skipped` is not `PASS`; `unavailable` is not `PASS`.
- **A local fix is not a remote SonarCloud closure.** The quality gate is not green until
  observed green. Validation must bind to the exact candidate revision.
- Re-query the issues API only after the corrected revision has been analyzed by SonarCloud
  (phase 8, under separate explicit push/analysis authority). Until then, report
  `PENDING_REMOTE_ANALYSIS` and claim no closure.

## Required artifacts

Emit alongside the loop's normal gate artifacts:

- `sonarcloud-issues-before.json` — secret-free raw snapshot (API metadata, project,
  branch/PR, analysis revision, issues, quality gate, measures).
- `SONARCLOUD_ISSUE_REGISTER.yaml` — per issue: key, rule, path, line, severity, type,
  validity, root_cause_cluster, disposition, evidence, candidate_fix, validation.
- `SONARCLOUD_ROOT_CAUSE_PLAN.yaml` — per cluster: id, root_cause, issue_keys, count,
  priority, minimal_fix, files, risk, validation, expected_impact.
- `SONARCLOUD_CHANGE_MANIFEST.yaml` — per change: file, symbol, change_type, cluster_id,
  issue_keys, reason, behavioral_impact.
- `SONARCLOUD_VALIDATION_REPORT.md` and `SONARCLOUD_REMEDIATION_REPORT.md` — evidence and
  verdict, with local disposition and remote status truthfully distinguished.

## Verdicts

`REMEDIATED_AND_REMOTE_VERIFIED` (candidate revision analyzed, target issue keys closed,
quality gate observed green) · `REMEDIATED_PENDING_REMOTE_ANALYSIS` (fixed + local-green, no
remote closure claimed) · `PARTIALLY_REMEDIATED` · `NO_VALID_DEFECTS` · `BLOCKED` ·
`INCONCLUSIVE`.

## Stop conditions

Stop before mutation if the project/branch is ambiguous, the analyzed revision cannot be
reconciled with local source, a cluster's root cause or correct owner is UNKNOWN, a fix
would require weakening a rule or gate, or unrelated user work would be overwritten. Never
expose the token. Never claim issue closure from local reasoning alone.
