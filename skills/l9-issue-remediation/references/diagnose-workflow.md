<!-- L9_META
l9_schema: 1
parent: l9-issue-remediation
layer: reference
role: diagnose_workflow
tags: [issues, diagnose, fleet, blockers, readiness]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-29
/L9_META -->

# Diagnose Workflow (auditor)

Read-only org issue readiness plus **already-resolved close** only. Never
commit, push, edit worktrees for fixes, or invoke `/l9-pr-remediation`.

## Usage

```text
/issues diagnose
/issues diagnose Quantum-L9/SEO-Bot
/issues diagnose Quantum-L9/SEO-Bot#5
```

Bare `/issues` is remediator Converge — not this workflow.

## Steps

1. **Bind fleet** — default org `Quantum-L9`, non-archived only:

```bash
python3 skills/l9-issue-remediation/scripts/fleet_discover.py --org Quantum-L9 --output fleet.json
```

If the user named a repo or issue, narrow ingest to that target (still may
fetch linked cross-repo refs from bodies).

2. **Ingest open issues**

```bash
python3 skills/l9-issue-remediation/scripts/issue_ingest.py --fleet fleet.json --output issues.json
# or single repo:
python3 skills/l9-issue-remediation/scripts/issue_ingest.py --repo Quantum-L9/SEO-Bot --output issues.json
```

GATE: issue snapshot fetched before any verdict.

3. **Verify existence (auditor)** — live `gh issue view` per
   [issue-verify.md](issue-verify.md). Do not treat ingest JSON as proof.
   Already-CLOSED / 404 → drop from the verdict list. OPEN but
   already-fixed / not-reproducible / does-not-exist → evidence-close
   (step 6). Never invent a replacement issue.

4. **Rank clusters** (leverage, not a single sticky pick):

```bash
python3 skills/l9-issue-remediation/scripts/cluster_rank.py --issues issues.json --output clusters.json
```

5. **Classify (read-only)** — ownership guess only; do not mutate code. Load
   [ownership-boundary.md](ownership-boundary.md) + [finding-classifier.md](finding-classifier.md).

6. **Already-resolved / phantom close** — if a linked PR is merged, the
   defect is gone, or verify said `not-reproducible` / `does-not-exist`,
   run `scripts/close_resolved_issue.py` with `--merged-pr`, `--commit`,
   or `--proof`. Still **never** chain `/l9-pr-remediation`. Confirm the
   gate:

```bash
python3 skills/l9-issue-remediation/scripts/open_issues_gate.py --intent diagnose --issues issues.json
```

Must print `diagnose_never_chains`.

7. **Present inline** — format below. Load `l9-ynp` when useful.

## Inline output

```markdown
## Fleet Issues Diagnose: Quantum-L9

**Repos scanned:** {n} | **Open issues:** {count} | **Clusters:** {k}

### Top blockers
| # | Issue | Ownership guess | Why blocking | Linked |
|---|-------|-----------------|--------------|--------|

### Cross-repo clusters
- {cluster_id}: {repos/issues} — shared cause hypothesis

### Already closed (auditor hygiene)
- {owner}/{repo}#{n} — evidence {merged PR or commit}

### Warnings
- …

**Diagnose Verdict:** CLEAN | ACTIONABLE | BLOCKED_HUMAN | BLOCKED_EXTERNAL

### YNP
**YES:** remediator `/issues` or `/l9-issue-remediation` on the ranked queue
**NO:** Hold — HUMAN/EXTERNAL only
**PROCEED:** do not start `/l9-pr-remediation` from Diagnose
```

## Enforcement

| Rule | Severity |
|------|----------|
| Skip issue ingest | HIGH — block verdict |
| Commit / push / fix during Diagnose | CRITICAL |
| Chain `/l9-pr-remediation` from Diagnose | CRITICAL |
| Alignment/gap/deep-eval theater | HIGH — do not emit |
