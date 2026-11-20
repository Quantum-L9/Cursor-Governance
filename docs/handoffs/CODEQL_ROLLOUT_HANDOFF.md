# Handoff Packet — CodeQL Org-Wide Rollout

<!-- --- L9_META ---
l9_schema: 1
artifact_type: handoff_packet
component: codeql_code_quality_rollout
tags: [handoff, ci, codeql, code-quality, security, governance, quantum-l9]
retrieval: on_demand
status: active
--- /L9_META --- -->

**GMP ID:** `GMP-L.3-codeql-org-rollout-2026-07-05`
**Handoff type:** AI-to-AI / AI-to-engineer · **Task type:** ci · **Autonomy:** L3 (constrained execution, human-approved writes)
**Owner org:** Quantum-L9 (`https://github.com/Quantum-L9`) · **Central repo:** `Quantum-L9/Cursor-Governance`
**Status:** Central layer is the two SHA-pinned callers in this packet. CodeQL stays in Cursor-Governance. It is not part of `l9-ci-core`.

---

## Objective

CodeQL implementation, query policy, the reusable workflow, and the default/extended suite split stay in Cursor-Governance. Do not add a CodeQL job to `l9-ci-core` `org-ci.yml` or to Core's required pull-request test job. Core keeps its own workflow inventory and its prevention of redundant full pytest suites on pull requests. A CodeQL workflow is a centrally governed security scanner, not one of those pytest violations.

Every other Quantum-L9 repo installs by replacing its CodeQL workflows with two callers. Neither caller uses `@main`. Both pin:

- reusable workflow `Quantum-L9/Cursor-Governance/.github/workflows/codeql-reusable.yml@24f0c4db99ba3ba170e5f872cd1c402684e47b81` (`actions: write`, CodeQL action `33d7b85d` / v4.39.3)
- pull-request config `Quantum-L9/Cursor-Governance/.github/codeql/codeql-config.yml@52d87ce2e217c16a96f0ef131f4da097ef7cd5e2` (default suite: no `queries`, no `query-filters`)
- nightly config `Quantum-L9/Cursor-Governance/.github/codeql/codeql-config-nightly.yml@52d87ce2e217c16a96f0ef131f4da097ef7cd5e2` (`security-extended`)

Copy these files, and no local `.github/codeql/` config:

- `docs/handoffs/codeql-caller-template.yml` → `.github/workflows/codeql.yml`. Push and pull request against the repository default branch. No schedule.
- `docs/handoffs/codeql-nightly-caller-template.yml` → `.github/workflows/codeql-nightly.yml`. Nightly `security-extended`. Not a pull-request check. The schedule runs from the default branch whatever that branch is named.

Cursor-Governance's own `.github/workflows/codeql.yml` is the self-scan. It passes the checkout config and is not the file other repos copy.

**Guardrails:**
- No workflow writes fixes back.
- A suppression belongs on the nightly config, one reason per rule id. A `queries` or `query-filters` key on the pull-request config disables overlay.
- Repos stay under `https://github.com/Quantum-L9/`.

---

## What already shipped in this repo (the central layer)

| File | Role |
|---|---|
| `.github/workflows/codeql-reusable.yml` | Reusable analysis at `24f0c4db`. Language detect, `build-mode`, `actions: write` so the default-branch run can save the overlay base. |
| `.github/codeql/codeql-config.yml` | Pull-request and default-branch suite at `52d87ce2`. No `queries`, no `query-filters`, `paths-ignore` includes tests. |
| `.github/codeql/codeql-config-nightly.yml` | Nightly `security-extended` config at the same commit. |
| `.github/workflows/codeql.yml` | This repo's self-scan. Local config path. Not the consumer install file. |
| `.github/workflows/codeql-nightly.yml` | This repo's nightly self-scan. Local nightly config. |
| `docs/handoffs/codeql-caller-template.yml` | The verbatim pull-request caller to copy into every other repo. |
| `docs/handoffs/codeql-nightly-caller-template.yml` | The verbatim nightly caller. `security-extended`, no pull request. |
| `docs/handoffs/CODEQL_ROLLOUT_HANDOFF.md` | This packet. |

---

## Fleet install

Scope: every non-archived repo under `https://github.com/Quantum-L9/` except `Cursor-Governance`. The install replaces CodeQL. It does not add a second scanner, and it does not assume the default branch is named `main`.

A CodeQL workflow is any `.github/workflows/*.yml` file that references `github/codeql-action/` or `codeql-reusable.yml`. The only two that remain are `.github/workflows/codeql.yml` and `.github/workflows/codeql-nightly.yml`.

Per target repo:

1. Read the default branch: `gh repo view Quantum-L9/<repo> --json defaultBranchRef --jq .defaultBranchRef.name`. Branch and open the pull request against that name.
2. Inventory workflows. Write the two templates over the canonical paths.
3. Delete every other CodeQL workflow and delete `.github/codeql/` when it exists. A leftover standalone workflow is a duplicate scan.
4. Leave default setup off when the callers are installed. Default setup disables the workflow file and rejects later CodeQL uploads. Its stored suite on this org is `extended`, which disables overlay.
5. Do not add these jobs to the repo's Core caller. `Analyze (central Core)` stays the required test check. CodeQL stays a separate security workflow.

The pull-request template gates the job with `github.event.repository.default_branch`, so the same file works when that branch is not `main`. The nightly schedule already runs from the default branch. GitHub registers `workflow_dispatch` for a workflow only after the file is on that default branch.

---

## Admin UI runbook (click-by-click)

**REQUIRED per repo — switch default → advanced setup** (default setup conflicts with the workflow; the pre-existing `github-code-quality` PR comments confirm scanning is already active on some repos):
1. Repo → **Settings**.
2. Sidebar → **Code security** (older label: *Code security and analysis*).
3. **Code scanning → CodeQL analysis**.
4. If **Default setup — Enabled**: **⋯ / Configure → Switch to advanced** → confirm. (Or toggle Default setup **off**.)
5. If already Advanced / not configured: nothing to do.

**Actions access (public repos):** none required — same-org reusable workflows are callable by default. (Only if a repo becomes private: Org → *Settings → Actions → General* and Cursor-Governance → *Settings → Actions → General → Access* → "Accessible from repositories in the organization.")

**Not part of this install:**
- Do not require the CodeQL check. `paths-ignore` skips docs-only pull requests, and a required check would then hang. The check also stays off the required set until a default-branch run has saved an overlay base and the job is no longer the long pole.
- Do not enable Copilot Autofix from this packet.

---

## Hosted evidence

Read from GitHub, not from the working tree alone.

| Evidence | Result |
|---|---|
| Reusable workflow `24f0c4db99ba3ba170e5f872cd1c402684e47b81` | `actions: write` is present. `actions: read` is absent. Default config is `codeql-config.yml@52d87ce2`. Action pin is `33d7b85d`. |
| Pull-request config `52d87ce2e217c16a96f0ef131f4da097ef7cd5e2` | No `queries` key. No `query-filters` key. `paths-ignore` is present. |
| Nightly config at that same commit | `queries: uses: security-extended`. |
| Pull request run [44652212018](https://github.com/Quantum-L9/Cursor-Governance/actions/runs/44652212018) on `#1067` | `Setting overlay database mode to overlay with caching because we are analyzing a pull request.` Then `No overlay-base database found in cache, reverting overlay database mode to none.` `Analyze (python)` succeeded in 3m49s. The cache miss is expected until a default-branch run saves the base. |
| Nightly execution | No hosted run. `workflow_dispatch` of `codeql-nightly.yml` returns 404 until that file is on the default branch. The schedule cannot fire before then. Do not record a nightly pass. |

---

## Phase 6 — Finalization / acceptance

Rollout is complete when, for every non-archived Quantum-L9 repo:
- [ ] The two caller templates are the only CodeQL workflows, on the repository default branch.
- [ ] No local `.github/codeql/` config and no standalone `github/codeql-action` workflow remains.
- [ ] Default setup stays off.
- [ ] A pull-request log shows overlay mode. A nightly log exists only after the nightly file has been on the default branch long enough to run.
- [ ] CodeQL is still not a required check and not a job inside Core's required pull-request workflow.

A later suite change is a new commit in Cursor-Governance and a new pin in both caller templates. Callers do not float on `@main`.

---

## DORA Block v2.0

```json
{
  "gmp_id": "GMP-L.3-codeql-org-rollout-2026-07-05",
  "task_type": "ci",
  "autonomy_level": "L3",
  "owner_org": "Quantum-L9",
  "central_repo": "Quantum-L9/Cursor-Governance",
  "audit_result": "PASS_STATIC_PENDING_RUNTIME",
  "confidence_static": 92,
  "guardrails": {
    "no_auto_commit": true,
    "source_suppression_only": true,
    "org_invariant_quantum_l9": true
  },
  "artifacts": [
    ".github/workflows/codeql-reusable.yml",
    ".github/codeql/codeql-config.yml",
    ".github/workflows/codeql.yml",
    ".github/codeql/codeql-config-nightly.yml",
    ".github/workflows/codeql-nightly.yml",
    "docs/handoffs/codeql-caller-template.yml",
    "docs/handoffs/codeql-nightly-caller-template.yml",
    "docs/handoffs/CODEQL_ROLLOUT_HANDOFF.md"
  ],
  "execution_tree": {
    "node": "codeql-org-rollout",
    "status": "SUCCESS_STATIC",
    "children": [
      {"node": "reusable-workflow", "status": "SUCCESS", "evidence": ["yaml_ok", "workflow_call", "per_language_build_mode"]},
      {"node": "shared-config", "status": "SUCCESS", "evidence": ["default_suite_no_queries_key", "nightly_security_extended", "tests_ignored"]},
      {"node": "caller-template", "status": "SUCCESS", "evidence": ["yaml_ok", "pure_uses_job", "security_events_write"]},
      {"node": "runtime-analysis", "status": "PULL_REQUEST_OVERLAY_OBSERVED", "evidence": ["actions_run_44652212018", "overlay_mode_then_cache_miss", "nightly_not_on_default_branch"]}
    ]
  },
  "next_action": "After this pull request is on the default branch, the nightly workflow can run. Fleet install then replaces standalone CodeQL workflows with the two pinned callers. Do not add CodeQL to l9-ci-core.",
  "source_intent_preserved": true,
  "scope_drift_detected": false
}
```

---

## Handoff acceptance checklist (for the receiving agent/engineer)

- [ ] Read the ownership decision. CodeQL stays in Cursor-Governance and out of `l9-ci-core`.
- [ ] Install the two pinned callers onto each repo's default branch, replacing standalone CodeQL workflows.
- [ ] Leave default setup off.
- [ ] Treat a nightly pass as unproven until a run exists after the nightly file is on the default branch.
