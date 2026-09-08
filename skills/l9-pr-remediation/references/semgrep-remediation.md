<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: semgrep_signal
tags: [semgrep, static-analysis, secrets, fail-closed, local-ce]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-09-05
/L9_META -->

# Semgrep remediation (App findings + local CE)

This reference governs the **Semgrep** signal: App findings retrieved in one
fail-closed GET, confirmed against current source, plus optional local
community-edition confirmation. Fix the authoritative owner. Never clear a
finding by suppression, config narrowing, or an authenticated App *scan*
(source upload) from this surface.

It shares the skill's single hot path (local-verify gate, one-commit-per-cycle).
Semgrep is **lazy**, like CodeQL and debt: ingest only when the check is failing,
annotations or logs show hits, or the user asks to fix Semgrep. Presence of
`.semgrep/` alone does **not** force a fetch on a green check. A red Semgrep check
is **not** a merge blocker unless `ops/autonomy/pr_board.py` lists it in the
required set.

## When this signal applies

- The **Semgrep**, **L9 Analysis**, or **pr-security** check is failing on the PR.
- CI logs or check annotations name Semgrep rules (`p/secrets`, `p/python`,
  `l9.*`, or a repo `.semgrep/` id).
- The user asks to "fix Semgrep findings", "clear the security scan", or
  "remediate the nosemgrep debt".
- A coverage gap is suspected (velocity scan hid `p/python` while CI ran full).

If a PR already exists, feed the baseline into the normal ingest / classify / fix
loop. Do not treat Semgrep as a second publish path and do not run `make pr` or
`make pr-check` to "confirm" it.

## Authority order (this signal)

1. Current user instruction.
2. Repository-local `AGENTS.md` (`L9_PR_SECURITY_VELOCITY_V1`),
   `scripts/semgrep_fetch.py` (App findings GET), and
   `ops/scripts/run_pr_security.sh` (local CE confirm — never an authenticated scan).
3. Active configs: `SEMGREP_CONFIGS` override, else velocity `p/secrets` plus
   `.semgrep/l9-pr.yml` when that file exists; full / CI adds `p/python`.
4. Current source and tests at the PR head.
5. Semgrep rule semantics — never a dashboard count or a CI summary screenshot.
6. `Unknown` — do not modify code solely because a rule fired.

## App GET vs local CE scan

Two different uses of Semgrep, and they do not share a credential path:

| Path | What | Token |
|---|---|---|
| **Retrieve** | `scripts/semgrep_fetch.py` — read-only `GET /deployments/{slug}/findings` | `capability_bind` resolves `SEMGREP_APP_TOKEN` in-process (env if already present, else Infisical CLI user profile, else AWS `openclaw-igorbot/semgrep#token`). Never print, paste, export, or write it. |
| **Confirm** | `ops/scripts/run_pr_security.sh` — local community edition | Child **unsets** the token so a CE scan cannot upgrade to an App upload (`l9.no-semgrep-app-token-in-child-env`). |

Never paste a token. The capability broker never shipped and is not the
delivery path — `capability_bind.py` is. A vault miss after bind is a real
miss (`docs/DEGRADED_MODE_CONTRACT.md`). An authenticated `semgrep ci` /
source-bundle scan stays out of band. A missing CE binary is `UNAVAILABLE`
on the publish security wave, never a silent PASS.

## Retrieve (App API first — full set, not GH trickles)

Do not reconstruct the finding set from `gh run view` logs or from MCP
`semgrep_findings` (default limit 10). Use the App API, paginated to completion:

```bash
# TEMPLATE — substitute owner/repo/PR from the current head
"${GOV_PY:-$PWD/.venv/bin/python}" scripts/semgrep_fetch.py \
  --repo "$OWNER/$REPO" --pull-request "$PR_NUMBER" \
  --output semgrep-findings-before.json
# branch analysis instead of a PR: --ref refs/heads/main
# explicit org: --deployment "$SEMGREP_DEPLOYMENT_SLUG"
```

The fetcher is stdlib-only, **read-only** (it never starts a scan or mutates
triage), binds the token in-process (`SEMGREP_APP_TOKEN` via
`capability_bind`, Authorization redacted in the receipt), pins the API host
(`semgrep.dev`), confines `--output` to the working tree, and is **fail-closed
on incomplete pagination** (a full page after the cap → `BLOCKED`). The App
API requires authentication; an unbound token is `BLOCKED`, never an empty pass.

Local CE confirmation (after the snapshot, not instead of it):

```bash
PR_SECURITY_PROFILE=velocity PR_SECURITY_MODE=gate \
  bash ops/scripts/run_pr_security.sh
```

Write any captured stdout under `$PWD` (never `/tmp`). MCP `user-semgrep` may
confirm a **cited file** already in the snapshot. It is not the snapshot SSOT.

Normalize each hit to the unified finding list with `source: semgrep`, its
`rule_name` / `check_id`, path, line, severity, and message.

## Confirm before fix

A finding is a mutation target only after it is confirmed against the current
revision:

1. Open the file at the PR head; locate the exact symbol and range.
2. Reproduce the rule condition; read callers, consumers, and related tests.
3. Check generated / vendored / excluded scope and whether velocity vs full
   configs explain a local/CI mismatch.
4. Decide validity — `CONFIRMED_DEFECT`, `CONFIRMED_SECRET_OR_INJECTION`,
   `VALID_HARDENING_GAP`, `FALSE_POSITIVE_CANDIDATE`, `STALE_FINDING`,
   `GENERATED_OR_VENDOR_SCOPE_ERROR`, `CONFIG_DRIFT`, or `UNKNOWN`.

Do not modify code solely because Semgrep reported it. A stale, generated, or
proven false-positive finding is recorded with evidence and **left unchanged**.

## Cluster by root cause, then prioritize

Collapse hits into the smallest set of independent root causes. Cluster by: same
`check_id` + pattern, same untrusted source or sink, same secret/logging helper,
same broad `except`, same path/SQL/command wrapper, same config defect.

Priority: confirmed secrets and credential construction → injection / command
exec / path traversal → SSRF and unsafe HTTP → shared causes closing many hits
→ `p/python` correctness on full/CI → velocity-only `p/secrets` residue →
`CONFIG_DRIFT` (local velocity vs CI full) → disputed / `UNKNOWN`.

## Minimal-fix contract

Fix the **authoritative owner**, once. Preserve public behavior, error semantics,
and security controls. Add no dependency, no unrelated formatting, no broad
refactor.

**Prohibited shortcuts** (any of these fails the cluster): `# nosemgrep` /
`nosemgrep:` as the fix, blanket rule ignore, dropping `p/python` or
`.semgrep/l9-pr.yml` from CI, emptying `SEMGREP_CONFIGS` to pass, lowering
severity, deleting tests, weakening assertions, swallowing exceptions, replacing
logic with a stub, pasting or reading `SEMGREP_APP_TOKEN`.

**Suppression** is allowed only when the finding is *proven* a false positive,
repo policy permits it, the rationale is documented adjacent to the code, and a
code-level fix would make the implementation less correct or less safe. Prefer
the existing `# nosemgrep: <rule-id>` form already used in this repo — never a
bare `# nosemgrep`.

## Validate — local CE vs remote CI are different truths

Remediator local verify **remains** `L9_REMEDIATOR=1 PR_BASE=origin/main make
precommit-repo`. A Semgrep re-run is confirmation of this signal, not a second
publish gate and not `make pr-security` as a shipping verb.

- `skipped` / missing binary is not `PASS`.
- A local CE clean on **velocity** configs is not a remote full-pack closure.
- Re-query the App API (`semgrep_fetch.py` on the published head) only after
  analysis has landed. Until then report `PENDING_REMOTE_ANALYSIS`. A still-red
  Semgrep check after re-query is work for the next cycle or a Deferred issue —
  it never holds the merge train unless `pr_board.py` says the check is required.

## Required artifacts

Emit alongside the loop's normal gate artifacts:

- `semgrep-findings-before.json` — secret-free App snapshot (deployment, scope,
  pagination receipt, normalized findings).
- Per finding in the PR ledger: `rule_name`, path, line, severity, validity,
  cluster, disposition, evidence (`source: semgrep`).
- Optional local CE profile (`velocity` / `full` / `SEMGREP_CONFIGS=…`) when a
  confirm scan ran.

## Verdicts

`REMEDIATED_AND_REMOTE_VERIFIED` · `REMEDIATED_PENDING_REMOTE_ANALYSIS` ·
`PARTIALLY_REMEDIATED` · `NO_VALID_DEFECTS` · `UNAVAILABLE` · `BLOCKED` ·
`INCONCLUSIVE`.

## Stop conditions

Stop before mutation if the failing check's configs cannot be reconciled with
local CE, a cluster's root cause or owner is `UNKNOWN`, the only way to clear a
hit is to weaken configs or add a bare `nosemgrep`, or someone asks to paste
`SEMGREP_APP_TOKEN`. Never claim remote closure from a local velocity run
alone.
