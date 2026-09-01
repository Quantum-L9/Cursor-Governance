# L9 Runtime Velocity — Progress (revision r1)

Assessed against **main@450b7d0** on 2026-08-30 — re-bound from `a2f78b5`, 109 commits later.

**11 done · 0 partial · 1 not started · 0 blocked · 0 unknown** (of 12).
Active queue 1 (**T8** only); 11 closed.

This is the pack's **first** progress record. The pack shipped its analysis, its plan and
its implementation without ever recording which units landed, so nothing is carried
forward: every record in `progress.yaml` was judged against the tree at `a2f78b5` and
against probes run in the live container on 2026-08-29, then re-bound to `450b7d0` on
2026-08-30 (see the update below). The counts above are the tally
over those 12 records and agree with `progress.yaml`'s stated `counts` by construction —
the sibling P307 pack documents that stating the two separately is how it came to carry
three different counts in three stores.

## What shipped

**Quantum-L9/Cursor-Governance PR#373**, squash-merged into `main` as `7df89e74` on
2026-08-28. 24 files, +2979 / −156.

Two things about that PR are worth recording, because a reader going back to it will be
misled otherwise:

* **Its body describes only its first commit.** It says *"Analysis only. No bootstrap or
  adapter code is changed by this commit"*, while the merged content carries the entire
  T1–T6 implementation plus three defects found during it. The body was never updated as
  the branch grew.
* **It merged clean despite conflicting with `main` at one point.** Five paths conflicted
  (`CLAUDE.md`, both `skill-registry.json` mirrors, `test_bootstrap_invariants.py`,
  `test_surface_profile.py`). The resolution kept `main`'s side on both test files, which
  matters — see the regression note below.

| Unit | Was | Now | Delivered | Left |
|---|---|---|---|---|
| **T1** | ⬜ | ✅ **done** | `ops/scripts/lib/workspace_roots.py` — one definition of "which repositories is this session working in", imported by `memory_prefetch` rather than re-derived. | Ordering is alphabetical then capped at 6, so a 7th repo is dropped by alphabet rather than relevance (P307 CI-005 R4). |
| **T2** | ⬜ | ✅ **done** | `reconcile_claude_commands.py` and `reconcile_llm_skill_adapters.py` iterate `projection_roots()`, so per-repo `.claude` mirrors are inside the reconcilers' target set. | — |
| **T3** | ⬜ | ✅ **done** | Per-repository fingerprint, install and stamp. Banner now reads `session-deps: 4/4 repositories cached and proven`, where it previously derived a container-root fingerprint from tool versions alone. | — |
| **T4** | ⬜ | ✅ **done** | `toolchain_proven()` gates the stamp: a failed install refuses the stamp and warns instead of reporting ready. | **P307 CI-028 R1 is not cleared by this** — the stamp is a bare `touch`, carrying neither the deps exit code nor a timestamp. Proof-gating and exit-code recording are different asks. |
| **T5** | ⬜ | ✅ **done** | Receipt freshness binds to the governance revision, not the clock alone. | — |
| **T6** | ⬜ | ✅ **done** | SessionStart runs the installer once per revision when the receipt is not `ready`, instead of printing its remediation string. | Whether it fired and could not repair, or did not fire, is not answerable from the receipt. Open probe. |
| **RC-6** | — | ✅ **done** | The cloud refresh skips its hard reset when the clone carries tracked modifications, names the skip in the banner, and records `reset-skipped-dirty`. The probe is `git status --porcelain`, never a stash. | P307 CI-015 R1 stays open — two governance checkouts exist in this container and nothing prints both paths with their revisions. |
| **RC-7** | — | ✅ **done** | The plans shelver resolves to the tracked `BUILT/` whenever it exists, so case-sensitive and case-insensitive platforms converge. | **10 tracked files still sat in `docs/plans/built/`**, committed by PR#354 before the fix existed. The fix stops regeneration; it does not clean what already landed. **8 of the 10 are folded into `BUILT/` here; 2 are withheld** — `pr_gate_velocity_25da307a` and `precommit_before_pr_408895ec` are also being moved into `BUILT/` by open PR #431, from the *root* copy rather than the `built/` copy, so both branches would add the same path with different bytes. Withheld rather than raced; see the note below. |
| **RC-8** | — | ✅ **done** | An uncomputable comparison is now distinct from an empty one: the resolver deepens a shallow clone once and retries, and exits naming the cause when no merge base exists even then. | — |
| **T7** | ⬜ | ⬜ **not started** | — | Rule 62 is still `version: 1.0.0`. |
| **T8** | ⬜ | ⬜ **not started** | — | `l9-cognitive-runtime` still carries no `CLAUDE.md`, `AGENTS.md`, `INVARIANTS.md` or `ARCHITECTURE.md`. |
| **T9** | ⬜ | ⬜ **not started** | — | The standing breakglass is unchanged. |

## Update 2026-08-30 — two units closed, one of them by someone else

**T7 done.** Rule 62 → v1.1.0 with a surface-transport section;
`surface_capabilities.github` added to `ops/autonomy/surface_profile.yaml`; a dated
*Observed GitHub transports* table in `docs/DEGRADED_MODE_CONTRACT.md`; dated
counter-observations on P307 CR-105/CR-124. This satisfies **T-CI102** in the live queue.

> **A correction worth keeping.** The first draft of that work explained the working
> `gh` route by saying capabilities "resolve through the broker, which keeps the
> credential on the far side." `main` then retired the capability broker as
> **never shipped** (`f855e90`, `14469c3`), and its own rule-62 bullet states that REST
> `gh api` is *the same openclaw PAT, not a second secret*. The draft was wrong, and it
> was wrong in a specific way: it recorded a **theory as a probe**. The replacement
> states only what is observable — `gh api` succeeds while this session's `GH_TOKEN` is
> an invalid sentinel — and explicitly declines to name the mechanism, because the
> repository cannot verify it. The finding the task existed for is untouched and was
> re-probed at `450b7d0`: **`gh auth status` reports the token invalid and exits 0.**
>
> **Re-probed again at integration (2026-08-31, `a221142`): same message, exit `1`.**
> The exit code is not stable across containers of this surface class. That is recorded
> as a dated counter-observation in `docs/DEGRADED_MODE_CONTRACT.md` rather than as a
> rewrite of the row above, and the standing rule text in `rules/62` and
> `surface_profile.yaml` now says the exit code disagrees with itself instead of
> asserting `0`. The rule the finding produced — never gate on `gh auth status` — is
> unchanged and better supported: an unstable signal is worse to gate on than a
> consistently inverted one.

**T9 done — by `#404`, not by this pack.** `ops/autonomy/breakglass_receipt.py` (schema
`l9.publish-path-breakglass.v1`) carries issuer, scope, reason, `issued_at` and
`expires_at`, and its docstring states a standing `L9_PUBLISH_PATH_OVERRIDE` string is
now inert. That is exactly T9's contract, delivered independently while this pack still
had it queued. Recorded as done and **attributed to `#404`** — claiming it would be the
easiest and least honest edit in this file.

### Two premises that evaporated

* The plan queued *"give bootstrap degradation a per-component recorded cause"* against a
  live receipt reading **5 of 8 components DEGRADED**. At `450b7d0` the receipt reports
  `state: ready`, **8/8 READY** — `#392` (Graphiti by transport) and the broker retirement
  removed the causes. The structural ask (components are still bare strings, not objects
  with a reason and a log path) survives as P307 CI-004 R3 and live-queue **T-CI004**, but
  there is now nothing degraded to demonstrate it on. Not built; recorded.
* The **P307 r2 pack is no longer the live queue.** `WIP/8-26-26-Claude Environment/_archive/DEPRECATED.md`
  demotes it to *"useful provenance"*. The live queue is
  `WIP/8-26-26-Claude Environment/PLAN_DOCUMENT.claude-env-pending-fixes.v1.json`. The
  targeted re-assessment recorded there is still accurate for the records it re-judged, and
  both of its files now say plainly that they are provenance.

### Two suspicions probed, both dismissed

The plan carried two observations that *looked* like defects. Both were probed before
being written up as findings, and both are non-defects. Recording them so the next
reader does not re-derive the same suspicion:

* **`workspace: /home/user` in the bootstrap receipt** looked like RC-1 residue — the
  container root where a repository was expected. It is deliberate. `install.sh`
  classifies the workspace explicitly and treats a multi-repo container root as a valid
  wiring target (`workspace ... is a multi-repo container root - wiring project
  artifacts`), refusing only when it is neither a repo, the harness project directory,
  nor a container root. The field records *where project artifacts are wired*, and the
  container root is the right answer.
* **"Did T6's installer fire, or fail silently?"** — I wrote earlier that the receipt
  could not tell you. That was wrong, and the earlier residual has been corrected: T6
  writes `~/.l9/claude/bootstrap-repair-<rev>.attempted` and `.log` per revision and
  reports SKIPPED / running / FAILED with the log head in the SessionStart banner. The
  answer was never meant to come from the receipt. In this container both markers exist
  (`a2f78b5` and `450b7d0`), the `450b7d0` log ends `Claude Code adapter: READY` with all
  nine components READY, and the receipt moved from 5/8 DEGRADED to 8/8 READY across
  exactly that boundary. **T6 works.**

### RC-6 caught a real loss in this session

SessionStart printed `WARN /root/.cursor-governance has uncommitted changes — reset
SKIPPED (refusing to discard in-flight work)`. The refresh would otherwise have hard-reset
the clone over six uncommitted T7 files. The guard shipped in `#373` for exactly this, and
this is its first recorded save.

## A regression that did not ship, recorded so it is not reintroduced

The branch re-pinned `test_profile_block_has_doctrine` to the literal string
`"Tree kernels are not an L4 phase"`. That was true at the branch's base `0fc6ee6`, but
`main` commit `2a45289` (PR#365) reworded the doctrine block to
`Tree kernels (kernels/Recursive Alignment.md) are not an L4 phase`, splitting the phrase
across a parenthetical. Verified against the real extractor at `a2f78b5`:

```
'Tree kernels are not an L4 phase'  -> False    # the branch's assertion
'kernel_gate.py'                    -> True     # main's assertion
'precommit-repo'                    -> True     # main's assertion
```

The conflict resolution kept `main`'s side, so the red assertion never landed. The lesson
is the general one: **an assertion pinned to a prose phrase is a latent regression against
any rewording.** `main`'s version pins the owner and the entry point instead, which is why
it survived a rewrite that would have broken the phrase.

## Unknowns

**U4 is resolved.** It asked whether anything besides `ops/autonomy/local_execution_gate.py`
reads `L9_PUBLISH_PATH_OVERRIDE`. Probed 2026-08-29: **three** code/config readers —
`local_execution_gate.py`, `ops/autonomy/surface_profile.yaml`, and
`ops/scripts/bootstrap_agent_environment.sh` — plus `ADAPTER_CONTRACT.md` and the generated
rule projection. T9 is a cross-surface contract change, not a single-site edit, and must
ship as its own PR.

U1, U2 and U3 were bound to T1–T3 and were resolved by their implementation.

## Cross-references into the P307 pack

This pack's remaining units are not new work — they are P307 active-queue records reached
from a different direction. Judging them in isolation would double-count:

| This pack | P307 record | Relationship |
|---|---|---|
| T5 | CI-004 R1 | **cleared** |
| T6 | CI-004 R2 | **cleared** |
| — | CI-004 R3 | still open: a reason string and log path per degraded component |
| T7 | CI-102 R1, CI-001 | CI-102 R1 names the deliverable — record the REST route as a sanctioned capability in `surface_profile.yaml` **and** rule 62 |
| T9 | CI-007 R1, R2 | the same change, described twice |
| T4 | CI-028 R1 | **not** cleared — see the table above |
| T1 | CI-005 R4 | enumeration half delivered; scope-ordering half open |
| RC-6 | CI-015 R1 | still open |
| RC-7, T8 | CI-031 | tracked-path hygiene |

## Next

T7, T8 and T9 in that order. T9 last and alone: it is the only unit that changes publish
authorization, and it now has three readers to keep consistent.

## RC-7 residue: the two files withheld from this branch

`docs/plans/built/` held ten tracked files. Eight are folded into `BUILT/` here.
Two are not:

| File | Why withheld |
|---|---|
| `pr_gate_velocity_25da307a.plan.md` | open PR #431 adds `docs/plans/BUILT/<name>` from `docs/plans/<name>` |
| `precommit_before_pr_408895ec.plan.md` | same |

Both branches would create the same destination path from a **different source
copy**, which is an add/add conflict, and the two sources are not equivalent: the
`built/` copy carries `status: completed` and `built: true` in its frontmatter and
the root copy does not. That is a content difference — the same class of judgement
`plan-copies-diverged` records — so it is not resolvable by picking whichever branch
merges first.

Withholding costs nothing recoverable: both copies remain on `main`, and the
`BUILT/` destination arrives via #431 regardless.

**The repo's own shelver then settled it, and not the way this pack proposed.** With
the two `built/` copies restored, the gate's generated-heal step moved the **root**
copies into `BUILT/` on its own — the same direction #431 takes, and byte-identical to
#431's blob at both paths (`26a3243c`, `a2fa8a99`). That output is committed here as
the shelver produced it. So the add/add conflict is resolved by the tooling that owns
the shelf rather than by whichever branch merged first, and both branches now make the
*same* change at those two paths, which merges clean.

**The follow-up is unchanged and now narrower:** `docs/plans/built/` still holds those
two lowercase copies, and they are the ones carrying `status: completed` / `built:
true`. Restoring those two frontmatter keys onto the `BUILT/` copy and dropping the
redundant `built/` copy finishes RC-7. It stays out of this branch because the key
restoration is the content judgement `plan-copies-diverged` records, not hygiene.
That finishes RC-7 without either branch overwriting the other's choice.
