<!-- L9_META
l9_schema: 1
parent: l9-issue-remediation
layer: reference
role: finding_classifier
tags: [issues, classify, cluster, severity]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-11
/L9_META -->

# Finding Classifier

Ownership first, then severity, then cluster by shared root cause.

## Order

1. **Ownership** — CODEBASE / CROSS_REPO / CI_PIPELINE / HUMAN / EXTERNAL / FALSE_POSITIVE
2. **Severity** — critical > high > medium > low (labels, title keywords, blast)
3. **Cluster** — group issues that share one fixable root cause across repos

## Clustering signals

- Explicit refs: `owner/repo#n`, full GitHub URLs
- Paired titles: “diverged between A and B”, “shared X”
- Same package/module name in titles/bodies
- Blocking language: “blocks”, “cannot install”, “unblocks”

## Sticky cluster selection (Converge)

Default: pick the single highest-ranked cluster that has at least one CODEBASE or
CROSS_REPO item. Prefer clusters that unblock the most dependent issues.

Ignore HUMAN/EXTERNAL-only clusters for mutation (Diagnose may still list them).

## Output shape (internal)

```json
{
  "clusters": [
    {
      "id": "cluster-1",
      "ownership": "CROSS_REPO",
      "severity": "high",
      "root_cause": "…",
      "owner_repo": "Quantum-L9/…",
      "issues": ["Quantum-L9/SEO-Bot#5", "Quantum-L9/Website-Bot#…"]
    }
  ]
}
```
