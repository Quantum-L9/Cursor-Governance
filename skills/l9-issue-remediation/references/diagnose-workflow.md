<!-- L9_META
l9_schema: 1
parent: l9-issue-remediation
layer: reference
role: diagnose_workflow
tags: [issues, diagnose, fleet, blockers, readiness]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-11
/L9_META -->

# Diagnose Workflow (read-only)

Read-only org issue readiness. **Never** commit, push, close issues, or edit
worktrees for fixes.

## Usage

```text
/issues
/issues Quantum-L9/SEO-Bot
/issues Quantum-L9/SEO-Bot#5
```

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

3. **Rank** — prioritize: Critical/High labels → cross-repo drift → blocked/blocking
   language → oldest updated. Cluster linked issues (body refs like
   `Quantum-L9/Website-Bot#…`, `SEO-Bot`/`website-bot` pairs).

4. **Classify (read-only)** — ownership guess only; do not mutate. Load
   [ownership-boundary.md](ownership-boundary.md) + [finding-classifier.md](finding-classifier.md).

5. **Present inline** — format below. Load `l9-ynp` when useful.

## Inline output

```markdown
## Fleet Issues Diagnose: Quantum-L9

**Repos scanned:** {n} | **Open issues:** {count} | **Clusters:** {k}

### Top blockers
| # | Issue | Ownership guess | Why blocking | Linked |
|---|-------|-----------------|--------------|--------|

### Cross-repo clusters
- {cluster_id}: {repos/issues} — shared cause hypothesis

### Warnings
- …

**Diagnose Verdict:** CLEAN | ACTIONABLE | BLOCKED_HUMAN | BLOCKED_EXTERNAL

### YNP
**YES:** Converge sticky cluster {owner}/{repo}#{n}
**NO:** Hold — HUMAN/EXTERNAL only
**PROCEED:** load l9-issue-remediation Converge on that cluster
```

## Enforcement

| Rule | Severity |
|------|----------|
| Skip issue ingest | HIGH — block verdict |
| Commit/push/close during Diagnose | CRITICAL |
| Alignment/gap/deep-eval theater | HIGH — do not emit |
