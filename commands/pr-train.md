---
name: pr-train
version: "1.1.0"
description: "Open a stacked PR train on the current branch, halt for remediator Converge, then /ff when open_pr=0"
auto_chain: ynp
dag: pr-train-v1
dag_file: workflows/dags/pr_train_dag.py
---

# /pr-train — stacked publish, halt for remediator, catch-up

**DAG-ENFORCED.** Execute `pr-train-v1` at `workflows/dags/pr_train_dag.py` (`LANGGRAPH_RUNTIME`).

One slash, three stops. The graph does **not** MERGE_TRAIN or write merge authorization.

1. **OPEN_TRAIN** — unique commits on the **current branch** (not every local ref). Same-path, generated-prefix clobber, and `git merge-tree` conflict stay one PR (unknown probe fail-closes). A colocated slice is all-or-nothing: one cherry-pick conflict onto the stack tip sends the **whole** group to remainder (do not publish a clean subset). Tip-preflight uses ``parent..sha`` (not a tree-merge of the whole ancestral commit). Remainder is unique blobs vs the tip (``git checkout sha -- path``, last writer wins), including filenames the tip already touched. Then remediator publish (`git push` of the extract + `gh pr create --base <stack-parent>` when the car is not the first onto main). Do not run `make pr`.
2. **REMEDIATE** — graph HALTS. Read `skills/l9-pr-remediation/SKILL.md` Converge. Do not run `make pr`.
3. **/ff** — `--ff-only` only when `open_pr_count == 0` (`skills/l9-repo-sync/scripts/ff.sh`)

## Usage

```
/pr-train
/pr-train --execute
/pr-train --ff-only
```

```bash
"$PWD/.venv/bin/python" workflows/dags/pr_train_dag.py --repo "$PWD" --execute
"$PWD/.venv/bin/python" workflows/dags/pr_train_dag.py --repo "$PWD" --ff-only
```

Plan-only (default): omit `--execute`. Widen inventory with `--all-refs` or `--ref`. Campaign branches halt unless `--campaign-override`.

## EXECUTION

1. Compile and run the graph. Do not skip stop 1.
2. After `--execute` opens PRs, status is `blocked` / `awaiting l9-pr-remediation Converge`. Sibling open-PR chains also halt here (collapse first). Do not run `make pr`.
3. After `open_pr=0`, `--ff-only`. Auto-chain `/ynp`.

## FORBIDDEN

- SessionDAG / `register_session_dag`
- Rebase, conflict resolution, force-push, sibling PRs onto main (later cars must ``--base`` the unique chain tip)
- Splitting merge-tree / generated-prefix collisions across stacked PRs
- Treating `--execute` as merge authorization or MERGE_TRAIN
- Inventorying every local ref unless `--all-refs`
- `/ff` / `--ff-only` while any PR is still open
- Pasting a DAG body into this file
