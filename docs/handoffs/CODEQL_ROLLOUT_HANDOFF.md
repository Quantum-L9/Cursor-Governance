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
**Status:** Central layer READY (this PR). Org rollout PENDING (this packet).

---

## Objective

Make CodeQL **security + code-quality** analysis org-wide from a **single source of truth**. This repo (`Cursor-Governance`) now hosts one **reusable workflow** + one **shared config**. Every other Quantum-L9 repo enables analysis by adding **one ~18-line thin caller** and deleting any local CodeQL config. Change analysis once here → it propagates to all callers pinned at `@main`.

**Non-negotiable guardrails (carry forward):**
- **No auto-commit, ever.** Copilot Autofix / reviewer suggestions stay suggestion-only; a human reads every diff and commits. No workflow writes fixes back.
- **Suppression is explicit** — via versioned `query-filters`/`paths-ignore`, never silent mass-dismissal.
- **Org invariant:** all repo routes stay under `https://github.com/Quantum-L9/`. No personal-account owners.

---

## What already shipped in this repo (the central layer)

| File | Role |
|---|---|
| `.github/workflows/codeql-reusable.yml` | Reusable (`workflow_call`) analysis: language auto-detect + per-language build-mode + `analyze`. |
| `.github/codeql/codeql-config.yml` | Shared query policy: `security-and-quality` suite, `query-filters: exclude precision:low`, `paths-ignore` incl. `tests/`. |
| `.github/workflows/codeql.yml` | This repo's own thin caller (self-scan). |
| `docs/handoffs/codeql-caller-template.yml` | The verbatim caller to copy into every other repo. |
| `docs/handoffs/CODEQL_ROLLOUT_HANDOFF.md` | This packet. |

---

## Phase 0 — TODO plan (org rollout)

Scope: every repo under `https://github.com/Quantum-L9/` except `Cursor-Governance` (already done). Risk: **LOW** (additive CI file; no source changes). Estimated: ~2 min/repo.

Per target repo:
- **TODO-1** CREATE `.github/workflows/codeql.yml` = `docs/handoffs/codeql-caller-template.yml` (verbatim). Risk LOW.
- **TODO-2** DELETE `.github/codeql/codeql-config.yml` and any standalone CodeQL workflow if present (config is centralized). Risk LOW.
- **TODO-3** ADMIN: if the repo has CodeQL **default setup** enabled, switch it to **advanced** (see runbook) so the caller runs. Risk LOW, but **required** — default setup blocks the workflow.
- **TODO-4** VERIFY per Phase 5. Risk LOW.

The caller (copy verbatim):

```yaml
name: "CodeQL (security + code quality)"
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
    paths-ignore: ["**/*.md", "docs/**", "**/*.mdc"]
  schedule:
    - cron: "24 3 * * 1"
  workflow_dispatch: {}
permissions:
  contents: read
  security-events: write
  actions: read
jobs:
  codeql:
    uses: Quantum-L9/Cursor-Governance/.github/workflows/codeql-reusable.yml@main
    permissions:
      contents: read
      security-events: write
      actions: read
```

### Sequencing (do not skip)
Callers pin `@main`; they only resolve **after this PR merges** the reusable workflow to `Cursor-Governance@main`. Order: **(1)** merge this PR → **(2)** roll callers to other repos → **(3)** verify. (To smoke-test before merge, temporarily pin a caller to `@claude/l9-ops-mcp-proof-gates-4ak2al`, then flip back to `@main`.)

### Rollout options
- **Manual:** in each repo, add the caller file via the GitHub UI ("Add file" → commit to a branch → PR).
- **Scripted (engineer with `gh` + write scope):** for each repo, drop the template at `.github/workflows/codeql.yml` on a branch and open a PR. Pseudocode:
  ```
  for repo in $(gh repo list Quantum-L9 --no-archived --json name -q '.[].name'); do
    [ "$repo" = "Cursor-Governance" ] && continue
    # add .github/workflows/codeql.yml (= codeql-caller-template.yml), rm local .github/codeql/, open PR
  done
  ```
  (Run by a human or automated session with write access to the target repositories.)

---

## Admin UI runbook (click-by-click)

**REQUIRED per repo — switch default → advanced setup** (default setup conflicts with the workflow; the pre-existing `github-code-quality` PR comments confirm scanning is already active on some repos):
1. Repo → **Settings**.
2. Sidebar → **Code security** (older label: *Code security and analysis*).
3. **Code scanning → CodeQL analysis**.
4. If **Default setup — Enabled**: **⋯ / Configure → Switch to advanced** → confirm. (Or toggle Default setup **off**.)
5. If already Advanced / not configured: nothing to do.

**Actions access (public repos):** none required — same-org reusable workflows are callable by default. (Only if a repo becomes private: Org → *Settings → Actions → General* and Cursor-Governance → *Settings → Actions → General → Access* → "Accessible from repositories in the organization.")

**DEFERRED — enable only when chosen:**
- **Copilot Autofix (suggestion-only):** Repo → *Settings → Code security → Code scanning → Copilot Autofix → Enable* (or org-wide via *Code security → Configurations*). Never auto-commits.
- **Required-check ruleset (baseline-first):** Repo/Org → *Settings → Rules → Rulesets → New branch ruleset* → target `main` → enforcement **Evaluate** (observe ~1–2 weeks) → **Require status checks** → add check `codeql` → **Create**; flip to **Active** after the baseline is triaged to zero. NOTE: with the item-2 `paths-ignore`, a docs-only PR skips CodeQL — a *required* check would then hang. Before making it required, add a companion "skip-guard" workflow reporting success on the complementary paths, required by the **`codeql`** job name.

---

## Phase 5 — Verification ladder

| Level | Check | Status | Confidence |
|---|---|---|---|
| 1 Syntax | `yaml.safe_load` on reusable wf, config, caller, template | ✅ SUCCESS | 95 |
| 2 Structure | reusable has `on.workflow_call`; caller job is pure `uses:` + `permissions`; `security-events: write` present | ✅ SUCCESS | 92 |
| 3 Detection logic | `detect` builder simulated on real language JSON → `python/none`; mixed & empty cases degrade correctly | ✅ SUCCESS | 90 |
| 4 Policy | config carries `security-and-quality` + `query-filters: precision:low` + `tests/` ignore | ✅ SUCCESS | 93 |
| 5 Runtime (end-to-end) | first Actions run invokes reusable wf, `Analyze (python)` uploads to Security tab | ⏳ PENDING (requires merge to `main` + a triggering PR/push) | n/a |

**Aggregate confidence (static layers 1–4): ~92/100.** Level 5 is deliberately **not claimed** — CodeQL cannot be executed without a GitHub-hosted runner; first real proof is the initial Actions run after merge. Do not report CI as passing until that run is green.

### How to complete Level 5 (post-merge)
1. After merge to `Cursor-Governance@main`, open/observe a PR in a caller repo.
2. **Actions** tab → run **"CodeQL (security + code quality)"** shows **"Reusable workflow: Quantum-L9/Cursor-Governance/…"**; `Analyze (python)` runs with **no autobuild step**.
3. **Security** tab → **Code scanning alerts** populated.
4. Docs-only PR → CodeQL **skipped**; code PR → **runs**. Low-precision findings absent.

---

## Phase 6 — Finalization / acceptance

Rollout is complete when, for every non-archived Quantum-L9 repo:
- [ ] `.github/workflows/codeql.yml` = the caller template (verbatim), merged to `main`.
- [ ] No local `.github/codeql/` config remains.
- [ ] Default setup switched to advanced (no conflict).
- [ ] Level 5 verified once (green Actions run + Security-tab alerts).
- [ ] Guardrails intact: no auto-commit automation added.

Future analysis/query/filter changes happen **once** in `Cursor-Governance/.github/codeql/codeql-config.yml` (or the reusable workflow) and propagate via `@main`.

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
    "docs/handoffs/codeql-caller-template.yml",
    "docs/handoffs/CODEQL_ROLLOUT_HANDOFF.md"
  ],
  "execution_tree": {
    "node": "codeql-org-rollout",
    "status": "SUCCESS_STATIC",
    "children": [
      {"node": "reusable-workflow", "status": "SUCCESS", "evidence": ["yaml_ok", "workflow_call", "per_language_build_mode"]},
      {"node": "shared-config", "status": "SUCCESS", "evidence": ["security_and_quality", "query_filters_precision_low", "tests_ignored"]},
      {"node": "caller-template", "status": "SUCCESS", "evidence": ["yaml_ok", "pure_uses_job", "security_events_write"]},
      {"node": "runtime-analysis", "status": "PENDING", "evidence": ["requires_merge_to_main", "requires_actions_run"]}
    ]
  },
  "next_action": "Merge this PR to Cursor-Governance@main, then roll the caller template to all non-archived Quantum-L9 repos and complete Level 5 verification.",
  "source_intent_preserved": true,
  "scope_drift_detected": false
}
```

---

## Handoff acceptance checklist (for the receiving agent/engineer)

- [ ] Read guardrails; confirm no auto-commit will be introduced.
- [ ] Confirm this PR is merged to `Cursor-Governance@main` **first**.
- [ ] Roll the caller template to each non-archived Quantum-L9 repo (Phase 0 TODOs).
- [ ] Run the admin runbook (switch default→advanced) per repo.
- [ ] Complete Level 5 verification; only then report CI green.
