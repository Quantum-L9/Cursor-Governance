# AGENTS.md — operating guide for `l9-cli-optimization` (generator id: optimize-cli-pr-pack)

Cross-tool agent instructions for this skill. `SKILL.md` is the authority; this
file is the fast operational map plus the nuances that are easy to miss. If the
two ever disagree, `SKILL.md` and the executable validators win.

## What this skill is

Turn an underutilized, verified, repository-owned capability into deployed code
and a reproducible PR commit pack. Two modes:

- **Standard optimization** — one capability at a time, full evidence/ledger/
  deploy/handoff pack. Refuses `dormant_by_design`.
- **Full-throttle activation** — enable off-by-default flags at scale, test-prove
  them, PR the flip. A bounded, opt-in exception to the `dormant_by_design` rule,
  for testing only.

## What it is NOT (rejections)

- Not an audit-only tool — it produces deployable code, not a report.
- Not a throttle / rate-limiter / pacing builder.
- Not a way to bypass provider quotas, billing, licensing, authorization, or abuse
  controls. Those flags are danger-class and are never flipped.
- Not a capability factory — it activates capability the repo already owns, it does
  not build new features from scratch.

## The single gate

```bash
python3 scripts/self_test.py     # aggregate gate: runs every validator + builds/validates packs (both modes)
```

Run it before delivering any change to the skill. It asserts, among much else,
that the `## Validation` script list in `SKILL.md` stays in **parity** with the
scripts it actually invokes. **If you add a script, add it to BOTH the `SKILL.md`
`## Validation` fenced block AND the `invoked` set in `self_test.py` (~line 63),
and make self_test actually run it — or parity fails.**

## Standard mode — flow

1. `scripts/scan_capabilities.py <repo>` — advisory diagnosis (inactive components,
   unwired executables, dangling/phantom/archived imports, syntax-broken files,
   off-by-default flags). Candidates are advisory; verify reachability before
   authoring a finding. `intent=staged_rollout` / `recommended_verdict=do_not_activate`
   is `dormant_by_design` — do NOT activate.
2. Run the two mandatory **manual diffs** (registry/inventory drift; config/doc
   references to deleted files) — the static scan cannot see these.
3. `scripts/measure.py --before <cmd> --after <cmd>` — comparable proof block
   (throughput, or `--capture` for a functional `0 → N` activation proof; use
   `--repo/--before-ref` for the unpatched baseline in a worktree).
4. `scripts/build_commit_pack.py --spec <spec> --repo-root <repo> --output <dir>`
   then `scripts/validate_commit_pack.py <pack-dir>`.

The pack builder is fail-closed: it exits 2 on external ownership, unsafe paths,
missing/unknown wiring, `dormant_by_design:true`, a fourth cycle, a worse
candidate, and more. Those refusals are load-bearing — do not weaken them.

## Full-throttle mode — flow

```bash
python3 scripts/flag_inventory.py <repo>                         # inventory + classification (read-only)
python3 scripts/full_throttle.py <repo> --mode plan              # would-flip set; mutates NOTHING
python3 scripts/full_throttle.py <repo> --mode apply \
        --test-cmd "<cmd>" --output ft.json                     # worktree flip + test + back-out
python3 scripts/build_flag_activation_pack.py \
        --report ft.json --repo-root <repo> --output <dir>      # review-required pack
python3 scripts/full_throttle.py <repoA> <repoB> --mode plan     # multi-repo matrix
```

Default `--mode plan`. Always plan and review danger exclusions before apply.

### Nuances (read before running full-throttle)

- **Two-polarity danger.** A flag is held when flipping it on *enables a dangerous
  action* (delete/purge/deploy/publish/charge/billing/live/prod/send/external/
  migrate/…) **or** *disables a safety control* (`disable_*`/`skip_*`/`bypass_*`
  over auth/tls/verify/validation/sandbox/permission/secret/…). Do not "simplify"
  this to a keyword list on names — the polarity is the point.
- **Staged flags are dormant_by_design.** `wave N`, `dormant_by_design`, and
  system-state intent mark a flag `staged`; it is never flipped. This keeps
  Identity-Lock #1 intact even inside this mode.
- **Empirical back-out is mandatory.** The classifier is not trusted alone. Apply
  mode runs the repo's own tests in a throwaway worktree; any flag whose activation
  regresses tests is reverted and reported `empirically_unsafe`. "All except a
  danger block-list" is thus proven, not assumed.
- **Isolation.** All flip+test happens in a `git worktree` at HEAD; the real
  working tree is never mutated. Apply mode requires a git repo and a test command
  (discovered or `--test-cmd`).
- **Never auto-merge.** The pack is `auto_merge=false`, `review_required=true`,
  labeled REVIEW REQUIRED. A human opens/merges the PR. The skill does not.
- **Danger test commands are refused.** A test command that itself deploys/publishes
  is danger-classified; apply mode refuses to run it.
- **BLOCKED is valid.** If every candidate is danger-excluded or regresses, the mode
  flips nothing and the pack builder exits 2. That is the honest outcome; do not
  force a flip.
- **Honesty.** `evidence/FULL_THROTTLE_REPORT.md` carries the real flags-off →
  flags-on test delta. Never fabricate an activation.
- **Adapter overrides.** `.optimize-scan.json` → `full_throttle.{never_flip,
  always_flip,danger_tokens}` extends the classifier per-repo.

### Full-throttle pack layout

```
MANIFEST.json                     strategy=full_throttle_flag_activation, auto_merge=false
change/files/<path>               flipped source (full content)
change/commit.patch               `git apply --index change/commit.patch`
pr/PR_BODY.md                     REVIEW REQUIRED — do not auto-merge
evidence/FULL_THROTTLE_REPORT.md  inventory, danger/staged/empirically-unsafe exclusions + reasons, test delta
SHA256SUMS
```

## Boundaries when editing this skill

### ✅ Always
- Keep `SKILL.md ## Validation` ↔ `self_test.py` invoked-set parity.
- Keep the standard pipeline's `dormant_by_design` refusal (`build_commit_pack.py`)
  and its negative self-tests green.
- Keep the danger classifier conservative — over-holding is safe, under-holding is
  not.
- Rebuild/re-run `scripts/self_test.py` after any change and before delivery.

### 🚫 Never
- Route full-throttle flips through `build_commit_pack.py` (it would reject them,
  and coupling the two defeats the isolation).
- Flip a danger or staged flag, a flag that regresses tests, or auto-merge a pack.
- Weaken a fail-closed refusal to make a build pass.
- Claim an activation without the captured test delta.

## Determinism & environment

- All scripts are stdlib-only. Packs are deterministic under `SOURCE_DATE_EPOCH`.
- Python 3.10+. `pip install -r requirements.txt` (jsonschema, PyYAML) for the
  standard pack builder/validators; the full-throttle scripts need no third-party
  deps.
