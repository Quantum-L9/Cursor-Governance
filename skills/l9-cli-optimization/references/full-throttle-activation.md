# Full-Throttle Activation Mode — sub-contract

A bounded, self-contained mode of `l9-cli-optimization`. It enables a
repository's off-by-default feature flags at scale, proves each against the
repository's own tests, and packages the flip as a **review-required** PR. It is
the answer to "test all repos full throttle": flip the flags on, back out
whatever breaks, and hand a human a PR that is safe to review.

This mode is the ONE place the skill relaxes **Identity-Lock #1's
`dormant_by_design` clause**, and only for testing. The core scan → PR-pack
pipeline (`scan_capabilities.py` → `build_commit_pack.py` → `validate_commit_pack.py`)
is untouched: it still refuses `dormant_by_design:true` (exit 2). The relaxation
is paid for with the compensating controls below; #2 (safety) and #3 (no external
quota / backpressure / auth bypass) remain absolute.

## Components

| Script | Role | Mutates? |
|--------|------|----------|
| `flag_inventory.py` | Enumerate off-by-default flags; polarity-aware danger classifier; single-line flip transform | No (read-only; `flip_flag` returns text) |
| `full_throttle.py` | Worktree harness: baseline → flip non-danger → empirical back-out; multi-repo driver | Only inside a throwaway `git worktree` |
| `build_flag_activation_pack.py` | Standalone deterministic pack builder (does NOT touch `build_commit_pack.py`) | Writes the pack output dir only |

## Classification (polarity-aware)

Flipping a flag `False → True`, the classifier assigns one of:

- **`danger` — never flipped.** Turning the flag on either
  - *enables a dangerous action*: `delete purge drop wipe destroy truncate erase
    deploy publish release push upload charge billing paid live prod send email
    webhook external remote network migrate overwrite auto` (token or destructive/
    financial/deploy substring), or
  - *disables a safety control*: name begins `disable_`/`bypass_`/`skip_`/`ignore_`/
    `no_`/`suppress_` over a safety root (`auth tls ssl verify validation sandbox
    permission secret encrypt audit limit quota csrf cors …`), or is self-evidently
    unsafe (`unsafe insecure unverified force no_verify allow_insecure`).
- **`staged` — never flipped.** The flag sits on a line carrying staged-rollout /
  `dormant_by_design` intent (`wave N`, `dormant_by_design`, system-state markers).
  This is Identity-Lock #1; the mode honors it.
- **`safe` — flip candidate.** Everything else — still validated by tests before it
  ships (see back-out).

Two further signals refine a `safe` flag before it is offered for flipping:

- **Consumer reachability (`consumer_evidence`, `needs_wiring`).** A flag is only a
  real flip candidate if something *reads* it. `flag_inventory` builds a repo-wide
  reader corpus (Load-context Names, attribute accesses, string keys — declarations
  and assignment targets excluded) and marks each flag `found` / `none` / `unknown`.
  A `safe` flag with `consumer_evidence == none` is **declared but unconsumed** —
  flipping it is a no-op — so it is held with `needs_wiring: true` ("needs a wiring
  change, not a flip"). This is the flag-level form of the skill's "never fake an
  activation" law (it is exactly the CEG `temporal_decay_enabled` case). `unknown`
  is a generic config leaf (`enabled` under a block) the static check cannot
  disambiguate; the decision is left unchanged and the block's parent identity must
  be verified manually (registry/adapter drift).
- **Non-runtime / infra scope (`scope`).** Config under `docs/`, `infra/`, `deploy/`,
  `helm/`, `monitoring/` (and `values*.yaml` / `Chart.yaml`) is `scope=non_runtime`;
  a generic `enabled` under a k8s/Helm deploy block (`ingress`, `autoscaling`,
  `pdb`, …) is `scope=infra`. Both are **surfaced but held** — they are documentation
  or deploy toggles, not application capability.

Adapter override in `.optimize-scan.json`:

```json
{ "full_throttle": {
    "never_flip":   ["experimental_x"],
    "always_flip":  ["enable_fast_path"],
    "danger_tokens":["ledger","settle"] } }
```

## Empirical back-out (the proof)

`full_throttle.py --mode apply` never trusts the classifier alone:

1. Add a throwaway `git worktree` at `HEAD` (the real tree is never touched).
2. Run the repo's own test command (discovered from pyproject/Makefile/package.json/
   tox, or `--test-cmd`) as **baseline** with flags off.
3. Flip every non-danger, non-staged candidate; run tests.
4. If tests regress, **bisect** (bounded group-halving) to isolate the breaking
   flag(s), revert them, reclassify `empirically_unsafe`, and re-run until green or
   the pass budget is spent.
5. The activated set = non-danger ∩ non-staged ∩ test-proven. Remove the worktree.

A deploy/publish **test command** is itself danger-classified and refused — the
mode never runs an external-effect command to "prove" a flag.

## Output

`build_flag_activation_pack.py` emits a deterministic pack:

```
MANIFEST.json                     strategy=full_throttle_flag_activation, auto_merge=false, review_required=true
README.md                         how to apply
change/files/<path>               flipped source (full content)
change/commit.patch               unified diff (applies with `git apply --index`)
pr/PR_BODY.md                     "REVIEW REQUIRED — do not auto-merge"
evidence/FULL_THROTTLE_REPORT.md  inventory, danger + staged + empirically-unsafe exclusions with reasons, real test delta
SHA256SUMS
```

The pack is **never auto-merged** by the skill. A run that can flip nothing (all
danger-excluded or all regress) emits a BLOCKED pack and exits 2 — a valid,
honest outcome, not a failure to force.

## Invariants (in addition to the core Identity Lock)

- Never flip a `danger`-classified or `staged`/`dormant_by_design` flag.
- Never flip a flag whose activation regresses the repo's own tests.
- Never mutate the real working tree; all flip+test runs in an isolated worktree.
- Never auto-merge; the PR is the human gate.
- Never fabricate an activation — the flags-off → flags-on test delta is real
  captured output.
- Never bypass external quota, billing, authorization, or abuse controls; those
  flags are danger-class by construction.
