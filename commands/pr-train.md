---
name: pr-train
version: "1.0.0"
description: "Open a stacked PR train, converge via l9-pr-remediation, then /ff when open_pr=0"
auto_chain: ynp
dag: pr-train-v1
dag_file: workflows/dags/pr_train_dag.py
---

# /pr-train — stacked publish, converge, catch-up

**DAG-ENFORCED.** Execute `pr-train-v1` at `workflows/dags/pr_train_dag.py` (`LANGGRAPH_RUNTIME`).

One slash, three stops in order:

1. **OPEN_TRAIN** — unique local commits onto stacked PRs. Same-path, generated-prefix clobber, and `git merge-tree` conflict stay one PR (unknown probe fail-closes into one PR). Then `PR_STACK=auto make pr`.
2. **REMEDIATE** — skill `l9-pr-remediation` Converge (merge authorization)
3. **/ff** — only when `open_pr_count == 0` (`skills/l9-repo-sync/scripts/ff.sh`)

## Usage

```
/pr-train
/pr-train --execute
```

```bash
"$PWD/.venv/bin/python" workflows/dags/pr_train_dag.py --repo "$PWD" --execute
```

Plan-only (default): omit `--execute`. Campaign branches halt unless `--campaign-override`.

## EXECUTION

1. Compile and run the graph. Do not skip stops.
2. Stop 2: read `skills/l9-pr-remediation/SKILL.md` Converge. Do not run `make pr`.
3. Stop 3: run `/ff` only after `open_pr=0`. Auto-chain `/ynp`.

## FORBIDDEN

- SessionDAG / `register_session_dag`
- Rebase, conflict resolution, force-push, sibling PRs onto main
- Splitting merge-tree / generated-prefix collisions across stacked PRs
- `/ff` while any PR is still open
- Pasting a DAG body into this file
