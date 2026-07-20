# Handoff Packet — Copilot Code Review Org-Wide Rollout

<!-- --- L9_META ---
l9_schema: 1
artifact_type: handoff_packet
component: copilot_code_review_rollout
tags: [handoff, ci, code-review, copilot, governance, quantum-l9]
retrieval: on_demand
status: active
--- /L9_META --- -->

**GMP ID:** `GMP-L.3-copilot-review-org-rollout-2026-07-05`
**Handoff type:** AI-to-AI / AI-to-engineer · **Task type:** ci · **Autonomy:** L3 (human-approved writes)
**Owner org:** Quantum-L9 (`https://github.com/Quantum-L9`) · **Central repo:** `Quantum-L9/Cursor-Governance`
**Status:** Instructions file READY here → PR open. Org rollout + auto-request ruleset PENDING (this packet).

---

## Objective

Add the **LLM reviewer layer** (Copilot code review) org-wide, **as code**, auto-run on every PR — without overlapping the deterministic tools (ruff, CodeQL `security-and-quality`, mypy). Two moving parts:
1. **`.github/copilot-instructions.md`** — steers *what* Copilot reviews (and what it must ignore). Read from the repo **being reviewed**, so it is **not inherited** from a central repo → it must be copied into each repo.
2. **Auto-request ruleset** — makes GitHub request a Copilot review on PR open/update, applied org-wide.

**Guardrails (carry forward):** suggestions only, **no auto-commit ever**; instructions are LLM nudges, **not enforcement** — hard invariants stay in deterministic gates (`L9-Ops-MCP/scripts/validate_org_invariants.py`, coding-kernel CI). Org invariant: all routes under `https://github.com/Quantum-L9/`.

---

## What shipped in this repo

| File | Role |
|---|---|
| `.github/copilot-instructions.md` | L9-tuned review instructions (anti-overlap with ruff/CodeQL/mypy + L9 house rules). Also the **canonical template** to copy to every repo. |
| `docs/handoffs/COPILOT_REVIEW_ROLLOUT_HANDOFF.md` | This packet. |

---

## Phase 0 — TODO plan (org rollout)

Scope: every non-archived repo under `https://github.com/Quantum-L9/`. Risk: **LOW** (adds a doc + a review request; no source or gate changes).

Per repo:
- **TODO-1** CREATE `.github/copilot-instructions.md` = this repo's file, **verbatim**. Risk LOW.
- **TODO-2** ADMIN: apply the auto-request ruleset (below). Risk LOW.
- **TODO-3** VERIFY (Phase 5). Risk LOW.

> `.github/copilot-instructions.md` is per-repo — there is no central-inherit. Copy it into each repo (same rollout shape as the CodeQL caller). Keep the copies in sync from this canonical one.

### Rollout options
- **Manual:** add the file via the GitHub UI in each repo (commit to a branch → PR).
- **Scripted (engineer with `gh` + write scope):**
  ```
  for repo in $(gh repo list Quantum-L9 --no-archived --json name -q '.[].name'); do
    # write .github/copilot-instructions.md (= this repo's file) on a branch, open a PR
  done
  ```
  (This AI session's write scope is limited to `L9-Ops-MCP` and `Cursor-Governance`; org-wide copy is handed off to an authorized session/engineer.)

---

## Admin runbook — auto-request Copilot review (the "ruleset snippet")

**Prerequisite:** a **Copilot Business or Enterprise** license. No license → no reviewer.

### Authoritative path — UI (reliable)
1. Org (or repo) → **Settings → Rules → Rulesets → New branch ruleset**.
2. Name it `copilot-review`; **Target branches** → include default branch (`main`).
3. Enable **"Request pull request review from Copilot"**.
4. Enforcement status → **Active**.
5. Org-wide: in the org ruleset, target repositories **All** (or by name pattern), excluding archived.
6. Save. Copilot is now auto-requested on PR open and re-requested on update.

### As-code path — ruleset JSON (import via UI or REST `POST /orgs/{org}/rulesets`)
Rulesets export/import as JSON, so the policy is versionable. **Verify the exact rule key against your GitHub version before relying on it** — the automatic-Copilot-review rule is newer and its JSON key may differ in your instance; the UI toggle above is the fallback source of truth.
```jsonc
{
  "name": "copilot-review",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    // Auto-request Copilot review. CONFIRM this rule's exact "type"/parameters
    // in your GitHub version (Settings > Rules exported JSON) before import.
    { "type": "pull_request", "parameters": { "automatic_copilot_code_review_enabled": true } }
  ]
}
```
> If your instance doesn't yet expose this as a ruleset rule, use the UI toggle (step 3) — same effect, just not captured in JSON.

### Optional central complement (UI, not code)
Copilot **Enterprise coding guidelines** (Org → *Settings → Copilot → Code review*) — natural-language rules scoped by file globs, enforced org-wide without a per-repo file. Complements (does not replace) the per-repo instructions file.

---

## Phase 5 — Verification ladder

| Level | Check | Status |
|---|---|---|
| 1 Structure | `copilot-instructions.md` present, tight, anti-overlap section unambiguous | ✅ SUCCESS |
| 2 Enablement | license active + `copilot-review` ruleset Active on target repos | ⏳ PENDING (admin) |
| 3 Runtime | open a PR → **Copilot** auto-requested as reviewer | ⏳ PENDING (live PR) |
| 4 Behavior | Copilot comments **respect** the instructions: does NOT nitpick line length; DOES flag a planted non-Quantum-L9 URL and a missing `L9_META` header | ⏳ PENDING (live PR) |

An LLM reviewer cannot be run locally; Levels 2–4 require enablement + a live PR. Do not report this as "working" until Level 4 is observed.

---

## Phase 6 — Finalization / acceptance

Complete when, for every non-archived Quantum-L9 repo:
- [ ] `.github/copilot-instructions.md` present (verbatim from canonical), merged to `main`.
- [ ] `copilot-review` ruleset Active (auto-request on PR open/update).
- [ ] Level 4 behavior observed once.
- [ ] Guardrails intact: no auto-commit automation; invariant enforcement still owned by deterministic gates.

---

## DORA Block v2.0

```json
{
  "gmp_id": "GMP-L.3-copilot-review-org-rollout-2026-07-05",
  "task_type": "ci",
  "autonomy_level": "L3",
  "owner_org": "Quantum-L9",
  "central_repo": "Quantum-L9/Cursor-Governance",
  "audit_result": "PASS_STATIC_PENDING_ENABLEMENT",
  "guardrails": {
    "no_auto_commit": true,
    "instructions_are_advisory_not_enforcement": true,
    "org_invariant_quantum_l9": true,
    "no_overlap_with_ruff_codeql_mypy": true
  },
  "artifacts": [
    ".github/copilot-instructions.md",
    "docs/handoffs/COPILOT_REVIEW_ROLLOUT_HANDOFF.md"
  ],
  "execution_tree": {
    "node": "copilot-review-rollout",
    "status": "SUCCESS_STATIC",
    "children": [
      {"node": "instructions-file", "status": "SUCCESS", "evidence": ["anti_overlap", "l9_house_rules", "suggestion_only"]},
      {"node": "auto-request-ruleset", "status": "PENDING", "evidence": ["requires_license", "verify_json_key_or_use_ui"]},
      {"node": "runtime-review", "status": "PENDING", "evidence": ["requires_live_pr"]}
    ]
  },
  "next_action": "Merge this PR, copy copilot-instructions.md to all non-archived Quantum-L9 repos, apply the copilot-review ruleset, and observe Level-4 behavior.",
  "source_intent_preserved": true,
  "scope_drift_detected": false
}
```

---

## Handoff acceptance checklist

- [ ] Confirm a Copilot Business/Enterprise license is active for the org.
- [ ] Merge this PR to `Cursor-Governance@main`.
- [ ] Copy `.github/copilot-instructions.md` to each non-archived Quantum-L9 repo.
- [ ] Apply the `copilot-review` ruleset org-wide (UI, or JSON after verifying the rule key).
- [ ] Observe Level-4 behavior on one live PR; only then report it working.
- [ ] Keep invariant enforcement in deterministic gates — do not make the LLM load-bearing.
