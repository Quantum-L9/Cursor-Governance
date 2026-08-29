# Friction map — L9 runtime velocity analysis

**Analyst role:** `environment_velocity_analyst`
**Evidence window:** session `cse_01Da5m2WsEqHvDLqGj2MV3wZ`, 2026-08-29, container `/home/user` (4 repositories)
**Contract under execution:** `l9cr-context-compiler-pr-pack-v2` against `Quantum-L9/l9-cognitive-runtime`
**Governance:** `main@0fc6ee6f2aadfbee885bf5bb708ff91c38205ba1`
**Prior art:** `WIP/8-26-26/environment_experience_improvement_pack_p307` (49 friction records, 37 improvements, 36 unbuilt)

Every row below is a measured observation from this container. Nothing is inferred from documentation alone. Claims that could not be resolved from available evidence are marked `UNKNOWN` and carry the probe that would resolve them.

---

## Root causes

### RC-1 — The bootstrap treats `WORKSPACE` as one repository; a cloud container holds many

`WORKSPACE` resolves to `/home/user`, the multi-repository container root. Two bootstrap planes consume it as if it were a repository checkout. One plane — memory hydration — does not, and it is the plane that works.

| Plane | Root handling | Outcome |
|---|---|---|
| Memory hydration (`memory_prefetch._hydration_roots`) | iterates children carrying `.git`, sorted, capped at 6 | correct — hydrated 4 of 4 repositories |
| Dependency provisioning (`session_deps_cloud.sh`) | uses the container root directly | installs nothing, reports success |
| Projection, project scope (`claude-code-project` adapter) | targets `/home/user/.claude` | per-repository mirrors are never reconciled |

**Evidence E1 — the dependency helper is a no-op that reports readiness.**
The helper fingerprints `uv.lock`, `pyproject.toml`, `requirements.txt`, `package.json`, `pnpm-lock.yaml`, `package-lock.yaml`, `.pre-commit-config.yaml` at `WORKSPACE`. `/home/user` holds none of them. The session fingerprint `9ff843f2c5497a1fd3d6b792a4899071d33d54f4ea709ef369cb0aaa1c3f8df1` was reproduced byte-for-byte from tool versions alone (`uv 0.8.17|node v22.22.2|pnpm 10.33.0|npm 10.9.7`), confirming zero manifests were seen. `toolchain_present()` tests `$WORKSPACE/.venv/bin/python` and `$WORKSPACE/node_modules`, neither of which can exist at a container root, so the cache branch is structurally unreachable. The install pass then finds no manifest and does nothing. `~/.l9/claude/deps-9ff843f2….log` contains exactly two lines: `installing workspace toolchain` and `install pass complete`. The banner said `session-deps: toolchain ready`.

**Evidence E2 — sixteen dangling bootstrap symlinks, four per repository.**

```
.claude/skills/l9-update-command    -> /root/.cursor-governance/skills/l9-update-command
.claude/skills/l9-harvest-pipeline  -> /root/.cursor-governance/skills/l9-harvest-pipeline
.claude/skills/l9-inspect           -> /root/.cursor-governance/skills/l9-inspect
.claude/commands/update-command.md  -> /root/.cursor-governance/commands/update-command.md
```

Those three skills are exactly the set this session's own `~/.l9/claude/projection-receipt.json` reports as `"removed"`. The reconciler *has* a stale-removal path (`for stale in sorted(previous - set(desired))` → `remove_managed`), and it ran — against `/root/.claude/skills` and `/home/user/.claude/skills`. The per-repository mirrors sit outside every adapter's target set, so nothing reclaims them. They are untracked and gitignored (`.gitignore:31:/.claude/`), i.e. pure bootstrap residue, present identically in all four repositories.

**Evidence E3 — that residue fails the in-scope repository's test suite.**

```
FAILED tests/test_gar_deployment_closure.py::test_missing_required_kernel_fails_pack_validation
FAILED tests/test_gar_deployment_closure.py::test_missing_routing_source_fails_pack_validation
2 failed, 182 passed in 63.57s
```

Both tests `shutil.copytree` the repository root; `copytree` raises on a dangling link. The working tree is otherwise clean. **A contract cannot begin from a green baseline in this repository, and the failure presents as a product defect.**

**Evidence E4 — repository environments never receive the lock refreshed in the same session.**
`l9-cognitive-runtime/uv.lock` was rewritten at 2026-08-29 01:46:57 by this session's clone; `.venv` dates from 2026-08-28 04:34:31. `uv sync --locked --extra dev --dry-run` reports three deltas — `cryptography 50.0.0 → 50.0.1`, the project itself stale, and `structlog==26.1.0` **absent entirely** while declared at `pyproject.toml:85`. Import smoke: `ModuleNotFoundError: No module named 'structlog'`. Separately, `l9-ci-core/.venv` contains seven entries (pyyaml and its stubs) against a repo with `pyproject.toml`, `uv.lock` and `.pre-commit-config.yaml`. Local results are therefore not reproducible against CI, which builds from the lock.

> **Prior-art delta.** P307 `PROGRESS.md` observed the same empty log and diagnosed it as *"session-deps asserts readiness without an import smoke."* That is the missing **detector**. RC-1 is the **cause**: the log is empty because the helper was pointed at a directory with nothing to install. An import smoke alone would have turned a silent failure into a loud one without fixing it.

---

### RC-2 — Readiness is time-bound, not revision-bound

`ops/scripts/claude_bootstrap_receipt.py` compares `now - generated_at` against `ttl_seconds` and returns UNKNOWN only on expiry. It carries `governance_revision` through to the caller but never compares it to live governance HEAD.

Observed: `~/.l9/claude/bootstrap-state.json` was written `2026-08-28T04:34:13Z` against `governance_revision b618338d…`, `state: DEGRADED`. Today, at `0fc6ee6f…`, it is 21 hours old — inside the 24-hour TTL — and its DEGRADED verdict is what the session banner reports. Meanwhile `gov-refresh.json` carries a 3600s TTL: readiness outlives the governance state it describes by a factor of 24.

`emit_bootstrap_status()` prints the receipt's own `remediation` string and never executes it. Nothing else does either. The consequence is a saturated signal: `make claude-env` exits **5** on every session — the documented meaning being *files correct, nothing loaded them* — so the one command `CLAUDE.md` names for "checking what is actually wired" always reports failure and therefore carries no information.

*Matches P307 CR-113 / CI-004, root-caused identically there, unbuilt.*

---

### RC-3 — Documented GitHub capability contradicts observed transport

Three sources disagree, and an agent can act on any of them:

| Source | Claim | Measured |
|---|---|---|
| Session system prompt | "You do NOT have access to the `gh` CLI" | `gh` is at `/usr/bin/gh` |
| `gh auth status` | "The token in GH_TOKEN is invalid" — **and exits 0** | true: `GH_TOKEN` is a 14-char `prox…` sentinel, not a PAT |
| `gh api repos/Quantum-L9/l9-cognitive-runtime` | — | **succeeds**, returns `Quantum-L9/l9-cognitive-runtime` |

`gh` works through the agent proxy despite the invalid token. Rule `62-github-openclaw-authority` instructs resolving an openclaw PAT and exporting it as `GH_TOKEN`; this surface is `model-controlled` and cannot hold one, so that path is unperformable here. P307 recorded CR-105 and CR-124 as *"no gh CLI exists"* — the current container falsifies both, so the prior record is now itself a source of wrong action.

---

### RC-4 — Repository law lives in the delivery pack, not the repository

`l9-cognitive-runtime` — the only in-scope repository — carries **no** `CLAUDE.md`, `AGENTS.md`, `INVARIANTS.md` or `ARCHITECTURE.md`. `Cursor-Governance` carries all five; `l9-meta-injector` three; `l9-ci-core` one. This is why `l9cr-context-compiler-pr-pack-v2` must ship `INVARIANTS.md` for verbatim copy as step 3 of its own execution order: every contract against this repository pays to re-import law that should already be resident.

---

### RC-5 — A one-time grant became standing configuration

`L9_PUBLISH_PATH_OVERRIDE=one-time breakglass authorized by user` is exported into every session. The authorization is described in its own value as one-time; the mechanism carrying it has no expiry. *Matches P307 CR-007 / CI-007, unbuilt.*

---

## Ranked improvements

Rank = (velocity gain × friction removed) ÷ effort. Low-leverage maintenance is rejected, not deferred.

### Local environment

| # | Change | Removes | Effort | Gain | Done when |
|---|---|---|---|---|---|
| R2 | Provision each detected repository from its own manifests; fingerprint and stamp per repository | E1, E4 | M | Local test results become reproducible against CI; a whole class of "works in CI, not here" disappears | `uv sync --locked --dry-run` reports zero deltas in every uv repository after SessionStart |
| R2b | Gate the stamp on applied state — lock-vs-environment probe plus an import smoke — not on attempted state | the false `toolchain ready` | S | Converts a silent failure into a caught one; the detector that would have found RC-1 on day one | no stamp and no readiness claim when the proof fails |
| R5 | Seed `CLAUDE.md` and `AGENTS.md` in `l9-cognitive-runtime` | RC-4 | S | Every future contract stops re-importing repository law | both files present; a pack no longer needs to ship `INVARIANTS.md` to establish authority |

### Bootstrap

| # | Change | Removes | Effort | Gain | Done when |
|---|---|---|---|---|---|
| R1 | Promote `_hydration_roots()` to a shared resolver; reconcile per-repository `.claude` mirrors through it | E2, E3 | S + M | Restores a green baseline in every consumer repository and stops the recurrence at each skill retirement | `find /home/user/*/.claude -xtype l` empty; `pytest -q` in the in-scope repo reports `184 passed` |
| R3 | Invalidate receipts on governance-revision change; re-run the installer once instead of reprinting a stale verdict | RC-2 | S + M | `make claude-env` becomes informative; degraded state stops being inherited across days | a receipt stamped with a superseded revision reads UNKNOWN; `make claude-env` exits 0 |
| R4 | Publish the observed GitHub transport truth-table; mark rule 62's PAT path inapplicable here; supersede CR-105/CR-124 | RC-3 | S | Removes a per-session detour and a false-negative signal | rule 62 names which transports are proven on a model-controlled surface |
| R6 | Replace the standing publish breakglass with a scoped expiring receipt | RC-5 | M (high risk) | Restores the meaning of "one-time" | the gate reads a receipt with `issued_at` and TTL, not an environment string |

**Rejected as low-leverage:** reclaiming superseded `deps-*.stamp` files (P307 CR-119 — five stamps, inert); receipt-CLI verb ergonomics (CR-127); receipt timezone-format inconsistency (`Z` vs `-10:00`). None changes an outcome.

---

## Expected gain and risk

| Change | Gain | Risk | Containment |
|---|---|---|---|
| R1 | Green baseline in 4 repositories; removes a defect that recurs on every skill retirement | removing a path inside a consumer repository | act only on projection-managed symlinks into the SSOT, `git check-ignore`-confirmed; refuse on any tracked path |
| R2 / R2b | Reproducible local runs; ends the CI-vs-local divergence class | per-repo work exceeds the 20s SessionStart budget | reuse the existing bounded-run and self-detach design; budget spans the loop, not each repository; helper stays fail-open |
| R3 | Readiness stops being saturated | a repair loop, since cloud SessionStart resets governance each session | per-session marker caps repair at one attempt; R3's first half ships alone if it does not converge |
| R4 | Removes a recurring detour | documenting a transport that later changes | record the probe, not the conclusion, so the table is re-derivable |
| R5 | Contracts stop re-importing law | root-file protection on the consumer | both files are new; no `ALLOW-ROOT-DELETION` marker needed |
| R6 | Restores one-time semantics | touches the publish gate | last, off the critical path; revert restores env-var behavior |

---

## Top 3 immediate changes

1. **Reconcile per-repository `.claude` mirrors** (R1). It is the only finding that fails tests *today*, in all four repositories, and it recurs every time governance retires a skill. Done when `find /home/user/*/.claude -xtype l` is empty and `pytest -q` in `l9-cognitive-runtime` reports `184 passed`.
2. **Provision dependencies per repository, and prove the install before claiming it** (R2 + R2b). Done when `uv sync --locked --dry-run` reports zero deltas in every uv repository after SessionStart and no stamp is written on an unproven install.
3. **Bind receipt freshness to the governance revision and repair once instead of reprinting** (R3). Done when a receipt carrying a superseded revision reads UNKNOWN and `make claude-env` exits 0.

R1 and R2 share RC-1 and are unblocked by the same twenty-line extraction: make `_hydration_roots()` the single answer to *which repositories is this session working in*.

---

## Unknowns

| id | question | why it matters | probe |
|---|---|---|---|
| U1 | Which component wrote the per-repository `.claude` mirrors, given the current project-scope adapter targets the container root? | decides whether R1 only cleans residue or must also stop an active writer | git history of `ops/scripts/claude_projection.py`, `ensure_workspace_wired.sh`, `migrate_claude_orphan_skills.py` |
| U2 | Do the two `test_gar_deployment_closure` failures also fail in this repository's CI? | decides whether E3 is container-only velocity loss or also a release blocker | read the CI run for `cc671c4` on `l9-cognitive-runtime` |
| U3 | Is the 6-root hydration cap the right bound for dependency provisioning, which is far costlier per repository? | sets whether R2 reuses the cap or takes a budget-derived bound | measure per-repository `uv sync` cost in this container |
| U4 | Does anything besides `ops/autonomy/local_execution_gate.py` read `L9_PUBLISH_PATH_OVERRIDE`? | decides whether R6 is one site or a cross-surface contract change | grep the governance tree and `surface_profile.yaml` |

None blocks starting R1. Each is bound to the change that must resolve it before its own implementation.

---

## Addendum — found while implementing the fixes (2026-08-29)

Three further defects surfaced during implementation, each with harder evidence
than anything in the original map because each one bit during this session.
All three are fixed on this branch.

### RC-6 — The cloud refresh hard-resets `$GOV` with no guard

`session_start_claude_governance.sh` resets the governance clone with
`git checkout -f -B main origin/main`. Correct for the ephemeral clone it was
written for; destructive anywhere else — it discards uncommitted changes and
moves HEAD off the checked-out branch.

Validating an edited hook end to end required `$HOME/.cursor-governance` to
resolve to the working checkout. The refresh then discarded that checkout's
uncommitted implementation and reset HEAD from the feature branch to
`origin/main`. Nothing warned; the receipt recorded an ordinary `fetched`. The
work survived only because it had been staged, so the blobs remained as
dangling objects and `git fsck --lost-found` recovered all eleven files.

This is P307 CR-010 ("multiple governance checkouts create wrong-tree risk")
made concrete: `/root/.cursor-governance` and `/home/user/Cursor-Governance`
are two distinct clones, and the hooks run from the former while the session
works in the latter.

**Fixed:** the reset is skipped when the clone has tracked modifications, and
the skip is named in the banner and recorded as `reset-skipped-dirty`. The
probe is `git status --porcelain`, never a stash — a probe that mutates to
measure state is the same class of defect. Untracked files are deliberately
not counted: `checkout -f` leaves them alone, and a fresh ephemeral clone
legitimately carries untracked bootstrap residue.

### RC-7 — The plans shelver un-tracks committed files on Linux

`skills/l9-pipeline-audit/scripts/audit_pipeline.py` shelved spent plans into
`plans_dir / "built"`. The tracked canonical shelf is `docs/plans/BUILT/`. On
the case-insensitive filesystem this repository is normally developed on those
are the same directory; on Linux, where the cloud containers run, they are not.

Every projection run therefore moved three tracked plans into a stray untracked
`built/`, showing as deletions plus untracked additions, and the plan gate then
failed on shelved plans carrying no kernel receipt. Restoring by hand did not
hold — the next run moved them again.

**Fixed:** the shelf resolves to the tracked `BUILT/` whenever it exists, so
both platforms converge on the directory under version control.

### RC-8 — The quality gate passed a branch it never looked at

The most severe finding of the session. The cloud SessionStart fetches the base
with `--depth 1`. Once `origin/main` advanced mid-session, it shared no
reachable ancestor with this branch:

```
$ git diff --name-only origin/main...HEAD
fatal: origin/main...HEAD: no merge base
$ git diff --name-only origin/main..HEAD | wc -l
117
```

`comparison_files()` ran `git merge-base` unguarded and the caller swallowed
the failure with `|| true`, so an undeterminable comparison became an empty
one. The gate then reported:

```
OK: nothing to gate vs origin/main (no committed or working-tree changes outside scratch)
RESULT: PASS — local PR gate clean (nothing to gate)
```

and wrote a PASS receipt, having run no checker at all on 117 changed files.
A gate that passes work it never examined is worse than no gate, and it fails
this way on every cloud session where the base moves.

**Fixed:** an uncomputable comparison is now distinct from an empty one. On a
shallow clone the resolver deepens once and retries — the history is missing,
not absent, and that alone recovered the real change set here. If no merge base
exists even then, it exits naming the cause rather than emitting silence. After
the fix the same gate run reports `PASS — local PR gate clean (changed files
only)` with 357 tests executed.

### Two pre-existing failures on `main`, also cleared

Both are byte-identical to `origin/main` here, so neither was caused by this
branch; both were introduced by `0fc6ee6` without updating the invariant that
guards them.

* `test_profile_block_has_doctrine` asserted the doctrine block names
  "Recursive Alignment". Kernels stopped being an L4 phase and the block now
  routes them through `kernel_gate.py` without naming the kernel. The assertion
  was updated to the contract the doctrine actually carries — not deleted, not
  skipped.
* The `run_pr_gate.sh` swallow ratchet stood at 10 against 15 occurrences.
  Re-baselined only after auditing all fifteen: every one is best-effort
  telemetry around a verdict carried elsewhere, and the two that could
  plausibly swallow a decision are compensated (`scratch_hold.py restore --all`
  by a separate fail-closed status check; the gate-failure receipt write runs
  in the already-failing path). The audit is recorded inline so the next raise
  must repeat it.

### What this addendum changes about the ranking

RC-8 outranks everything in the original list: a false PASS in the quality gate
silently removes the guarantee every other change depends on. RC-6 is second —
it destroys work rather than merely wasting time. Both were invisible to the
original analysis because neither shows up until you *act* in the environment
rather than measure it, which is the general lesson: the friction map found what
was slow, and implementation found what was unsound.
