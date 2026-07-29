# Convergence and Failure Rules

## Maximum passes

Run no more than three implementation-validation passes. A pass must change code, evidence, or blocker understanding. Repeating the same checks without a changed hypothesis is not a pass.

## Stop early when

- all PR-ready gates pass;
- the generated pack validates;
- no material unknown affects deployability;
- remaining work is explicitly external and assigned.

## Block when

- bottleneck ownership, baseline, or correctness invariants are materially ambiguous;
- repository state cannot be separated from unrelated changes;
- core validation is unavailable and no equivalent proof exists;
- deployment requires unknown irreversible actions or unsafe resource expansion;
- patch and copied files cannot be reconciled.

## Issue artifacts

After the third pass, create one issue file per independent root cause. Deduplicate by a stable fingerprint based on subsystem, symptom, and ownership.

Each issue must include:

- title;
- owner or receiving agent;
- observed failure;
- evidence;
- root-cause assessment and confidence;
- affected paths or systems;
- reproduction steps;
- acceptance criteria;
- safe next action;
- scope exclusions.

Do not combine unrelated root causes into a single catch-all issue.
