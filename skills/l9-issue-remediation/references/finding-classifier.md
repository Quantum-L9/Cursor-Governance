<!-- L9_META
l9_schema: 1
parent: l9-issue-remediation
layer: reference
role: finding_classifier
tags: [issues, classify, cluster, severity, leverage]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-29
/L9_META -->

# Finding Classifier

Ownership first, then severity, then cluster by shared root cause, then
**leverage rank the whole queue**.

## Order

1. **Ownership** — CODEBASE / CROSS_REPO / CI_PIPELINE / HUMAN / EXTERNAL / FALSE_POSITIVE
2. **Severity** — critical > high > medium > low (labels, title keywords, blast)
3. **Cluster** — group issues that share one fixable root cause across repos
4. **Rank** — `scripts/cluster_rank.py` (not a single sticky pick)

## Clustering signals

- Explicit refs: `owner/repo#n`, full GitHub URLs
- Paired titles: “diverged between A and B”, “shared X”
- Same package/module name in titles/bodies
- Blocking language: “blocks”, “cannot install”, “unblocks”

## Queue (Converge)

Default `max_clusters_per_invoke: all`. Drain every automatable cluster
highest leverage first:

1. Shared root cause that unblocks the most linked issues
2. Cross-repo blast (one owner fix, many consumers)
3. Severity
4. Oldest updated as tie-break

Ignore HUMAN/EXTERNAL-only clusters for mutation (Diagnose may still list
them). They remain OPEN and keep `open_issues > 0` unless evidence-closed.

Independent owning repos may run in parallel; dependent clusters stay serial.

## Output shape (internal)

```json
{
  "clusters": [
    {
      "id": "cluster-1",
      "ownership": "CROSS_REPO",
      "severity": "high",
      "root_cause": "shared-link",
      "owner_repo": "Quantum-L9/…",
      "issues": ["Quantum-L9/SEO-Bot#5", "Quantum-L9/Website-Bot#…"],
      "leverage_rank": 1,
      "automatable": true
    }
  ]
}
```
