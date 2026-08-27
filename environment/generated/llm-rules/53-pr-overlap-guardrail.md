---
description: Before opening any PR, the pre-open overlap gate must pass; a branch conflicting with its own base is blocked outright, and work overlapping an open PR routes into that PR or stacks on its head, never a sibling PR that conflicts.
---

# PR overlap guardrail (PR_OVERLAP_GUARDRAIL_V1)

The only sanctioned publish path (`make pr` → `open_pr_after_gate.sh`) runs
`ops/scripts/pr_overlap_check.py` between the L4 release check and `git push`.
The gate detects whether the current branch textually conflicts with its own
base or with any already-open PR in the same repo, and blocks BEFORE the push
with routing instructions. Raw `git push` / `gh pr create` are off doctrine but
not blocked (CANONICAL_LAW §6.2.4); prefer `make pr` because it runs this gate,
not because the alternative errors.

## Base probe (runs first)

Before any open-PR reasoning, `base_conflicts()` probes HEAD against the
freshly fetched `PR_BASE` with the same `git merge-tree --write-tree` test and
blocks on non-generated conflicts.

It runs **first** because the open-PR path short-circuits: with nothing else
open the gate used to print `PASS: no other open PRs to overlap` and return —
and that is exactly the state a branch duplicating already-merged work arrives
in. Merged work is not an open PR any more, so the open-PR probe is
structurally blind to it. PR #319 was that case: a second architecture compiler
built in parallel with the one already on `main`, add/add-conflicting with its
base on 28 paths, published clean and caught only by reading the diff by hand.

Unlike the open-PR probe there is no changed-files filter. A conflict against
the base is by construction one this branch's own side caused; the only paths
merge-tree can name outside the three-dot diff are directory/file collisions,
which must block too. Generated paths stay exempt.

`PR_OVERLAP` governs it identically (`block` / `warn` / `ignore`), and an
unavailable probe is a telemetry failure under the same policy below. On a hit:
refresh from the base and resolve, or close the branch if the work is already
merged. Do not route around it — a base conflict is not a stacking candidate.

## Overlap gate

| Knob | Behavior |
|------|----------|
| `PR_OVERLAP=block` (default) | Fail closed pre-push on a non-generated textual conflict with an open PR; names the PR, head branch, files, and routing options |
| `PR_OVERLAP=warn` | Same detection, but proceeds with a WARN (exit 0) |
| `PR_OVERLAP=ignore` | Skips the gate — only with stated justification |
| `PR_STACK=auto` (`make pr` default) | Instead of blocking, re-resolves the PR base to the overlapping open PR's head branch (never main) when the blocking set is one unambiguous chain; ambiguous sibling chains still block |
| `PR_STACK=` | Opt out: keep `PR_BASE` (usually `origin/main`); overlap still blocks |

Detection is REST-only (`gh api`): open PR list → per-PR file lists →
filename intersection with `git diff --name-only $PR_BASE...HEAD` →
`git merge-tree --write-tree` textual probe (git ≥ 2.38) to distinguish
same-file/disjoint hunks from a real conflict.

Failure policy: **autonomous publication fails closed on missing telemetry**
(gh absent, api failure, unresolvable repo identity, unreadable changed files)
— an undeterminable collision state is not publishable
(`96-multi-agent-main-bound-execution`, E6). Only the push is blocked; local
isolated work stays valid. An interactive human run still degrades to a WARN,
since a person can read it and judge. Override either way with
`PR_OVERLAP_TELEMETRY=closed|open`. Fail-open on precision, fail-closed on the
decision (no probe ⇒ filename overlap still blocks); fail-closed on a detected
non-generated textual conflict.

The gate runs against the base ref that `open_pr_after_gate.sh` fetches
immediately beforehand, so overlap is judged against the *current* origin/main
rather than the task's original BASE_SHA (E5).

## On overlap: preferred order

1. **Commit into the same-agent open PR branch** — the work belongs to that
   PR; do not open a sibling.
2. **Stack** — default for `make pr`. Opt out with `PR_STACK= make pr`
   to publish against `main`. Policy: rebase and conflict resolution
   forbidden; bottom-up merge order. A stack parent must use `--merge`
   or children must land first.
3. **`PR_OVERLAP=ignore`** — only with a stated justification.

## Generated artifacts

Paths under `GENERATED_PATH_PREFIXES` (`ops/scripts/sync_generated_artifacts.py`
— run `--print-generated-prefixes` for the live list) are exempt from overlap
blocking: their conflicts self-resolve.

- `.gitattributes` attributes them `merge=l9-generated`; the driver
  (`ops/scripts/git_merge_driver_generated.sh`) keeps ours and appends the
  path to `.l9/pr/regen-required.txt`.
- `ops/scripts/ensure_git_merge_drivers.sh` registers the driver per-clone
  (git config is not tracked); `check_governance_wiring.sh` self-heals it
  every session.
- **Regen obligation:** whenever `.l9/pr/regen-required.txt` lists paths, or
  any merge touched generated paths, run
  `python3 ops/scripts/sync_generated_artifacts.py --force`, stage, and commit
  before opening or updating a PR. A merge is not complete while the marker
  is non-empty.
- `skills/AUTONOMY_MANIFEST.yaml` is intentionally NOT attributed to the
  driver: it is the hand-authored routing SSOT (only orphan-heal mutates it),
  and keep-ours could silently drop hand-authored tier edits regeneration
  cannot restore. Concurrent same-line edits to it still block via the gate's
  probe.

## Guardrail, not proof

The gate is a guardrail, not a correctness proof: rename/semantic conflicts
can slip past a clean merge-tree probe, and CI plus remediation remain the
final word. Disabling without justification is a violation.

<!-- generated-from: rules/53-pr-overlap-guardrail.mdc; do-not-edit -->
