# Pre-commit / generated-artifact bugfix brief

## Executive verdict

`CURSOR_GOVERNANCE_PRECOMMIT_BUGS_FIXED_AND_REGRESSION_PROVEN`, with one
unrelated pre-existing finding recorded and deferred (below).

One root cause, fixed at one owner: the governance `trailing-whitespace` hook
was not Markdown-aware, so it destroyed two-space hard line breaks in every
repository the gate touches. The supplied evidence proposed
`--markdown-linebreak-ext=md`; that would have been an **incomplete** fix. The
shipped fix is `--markdown-linebreak-ext=md,mdc`.

The second suspected defect — generic writers independently canonicalizing
generator-owned artifacts — was investigated and **measured**, not assumed. It
has exactly one manifestation, closed by the same one-line fix. No new
generated-path registry was created, because the measurement showed one would
be a no-op.

## Exact SHA

Base: `a75e5de993ec5dbead494b60ca62eb256a7046c5`
(`main@a75e5de`, "feat(surfaces): diverge Claude gate hooks from Cursor at
l9_hook_exec (#487)").

## Bug 1 — Markdown hard breaks destroyed

**Expected:** two trailing spaces on a non-blank Markdown line are a hard line
break and must survive whitespace cleanup.
**Actual:** they were stripped from every `.md` and `.mdc` file the gate saw.

**Blast radius is fleet-wide, not governance-local.** `run_pr_precommit.sh:46-51`
and `:157` run the **governance** config as the authority against **consumer**
workspaces:

```bash
SKIP="$skip" pre-commit run --config "$GOV_PRECOMMIT_CONFIG" --files "${files[@]}"
```

So a consumer whose own `.pre-commit-config.yaml` contains only ruff hooks
(l9-harness) still gets governance's `trailing-whitespace`.

**Proven chain, from source rather than inference:**

1. `l9-harness/scripts/update_manifest.py:58-59` emits literal hard breaks:
   `f"Package: \`{PROJECT['name']}\`  "`.
2. The unflagged hook strips them (upstream `_process_line`: with
   `is_markdown=False` the line is `rstrip()`ed unconditionally).
3. `l9-harness/scripts/verify_generated.py:30-38` compares **raw bytes**
   before/after regeneration and raises `generated artifact drift: MANIFEST.md`.

That is a true oscillation with no fixed point: the generator restores the
bytes, the gate strips them again, forever.

## Bug 2 — generated-artifact ownership

Investigated as a distinct defect class, then **measured**.

`is_generated_path()` (`ops/scripts/sync_generated_artifacts.py:85-93`) is the
single generated-path authority, and its `GENERATED_PATH_PREFIXES` are
governance-local. Consumers have no entry — confirmed by
`ops/scripts/ensure_git_merge_drivers.sh:8` ("consumer repos legitimately have
no `merge=l9-generated` entries"). No repo-side generated declaration exists,
and the writer hooks do not consult that authority for file selection at all.

So the exposure is real in principle. The question is whether anything else
actually falls through it. Both mutating writers were run against **all eight**
of l9-harness's declared generated targets (`verify_generated.py:8-17`), on
copies:

| Writer | Result |
|---|---|
| `trailing-whitespace` (with fix) | `exit=0` — nothing modified |
| `end-of-file-fixer` | `exit=0` — nothing modified |

**The Markdown hard break was the only manifestation.** Adding a generated-path
exclusion mechanism would therefore have changed no observed behavior, while
creating the second generated-path authority the task explicitly prohibits.
Recorded as hardening (P2), not built.

## Root causes

| ID | Severity | Owner | Cause |
|---|---|---|---|
| F1 | P0 generated integrity | `.pre-commit-config.yaml:23` | `trailing-whitespace` declared no `--markdown-linebreak-ext`, so Markdown hard breaks were stripped fleet-wide, producing byte-level drift against generator-owned artifacts. |
| F2 | P1 precommit correctness | `.pre-commit-config.yaml:23` | Protecting only `md` leaves `rules/*.mdc` unprotected; `project_llm_rules.py` copies `.mdc` bodies verbatim into `environment/generated/llm-rules/*.md`, so the loss regenerates into a generated file. |
| F3 | P2 hardening | `sync_generated_artifacts.py:64-93` | Generated-path authority is governance-local and is not consulted by writer file selection. Currently unexercised (measured above). Not fixed — see Remaining debt. |

### Why `mdc` was required (F2)

This is the part the supplied evidence did not reach. Three `.mdc` rule sources
carry hard breaks, and two of their generated `.md` projections do — the same
two files, confirming verbatim body propagation (`project_llm_rules.py:79-92`,
`build_projected_text`).

Running the real pinned hook on the real governance content:

| Configuration | `rules/93-….mdc` (source) | `environment/generated/llm-rules/93-….md` |
|---|---|---|
| no args (pre-fix) | rewritten | rewritten |
| `…=md` (as suggested by evidence) | **still rewritten** | protected |
| `…=md,mdc` (shipped) | protected | protected |

The middle row is the trap: it protects the projection while stripping its
source, so the next `sync_generated_artifacts` run propagates the loss into a
now-"protected" generated file. That is the same oscillation, relocated.

## Exact repair

`.pre-commit-config.yaml`, one hook, one argument:

```yaml
      - id: trailing-whitespace
        args: ["--markdown-linebreak-ext=md,mdc"]
        exclude: "^(dist/|docs/plans/claude-code/[^/]+/)"
```

`ops/config/precommit-hook-contract.json` — the `trailing-whitespace` note now
records the exception so it cannot silently regress. `mode` stays `writer`.

## Why the fix is generic

- Extension-scoped, not filename-scoped. No `MANIFEST.md` special case, no
  repository special case, no generator-specific branch.
- Uses the pinned hook's own purpose-built option, verified present in the
  installed `v6.0.0` source (`--markdown-linebreak-ext`, `action='append'`),
  with argument normalization checked (`md,mdc` → `['.md', '.mdc']`).
- One owner. No second registry, no duplicated generated-path authority.
- `trailing-whitespace` is not disabled, Markdown is not excluded, and
  generated verification is untouched — strictly stronger, never weakened.

## Authored-Markdown behavior after fix

Narrow by construction in upstream `_process_line`, which requires
`is_markdown and (not line.isspace()) and line.endswith(b'  ')`:

| Case | Behavior |
|---|---|
| Non-blank line + two trailing spaces | **preserved** (hard break) |
| Single trailing space | still removed |
| Whitespace-only line | still emptied |
| Non-Markdown file (`.txt`, `.py`, …) | unaffected by the flag |
| Line ending in 3+ spaces | normalized to exactly 2 (upstream semantics; cannot infer intent) |

Measured on a repo-wide `--all-files` sweep: **0** true hard breaks removed,
**34** whitespace-only lines still cleaned. Ordinary hygiene is intact.

## Generated-artifact behavior after fix

`python3 ops/scripts/sync_generated_artifacts.py --force --pe-manifest`
produced **no** generated drift. The real `l9-harness/MANIFEST.md` now passes
the governance writer unchanged, and its two hard breaks survive regeneration
byte-for-byte.

## Sibling writer disposition

| Writer | Disposition |
|---|---|
| `trailing-whitespace` | fixed (F1/F2) |
| `end-of-file-fixer` | no change needed — measured `exit=0` across all harness generated targets; its existing `dist/` exclusion already covers the known no-trailing-newline case |
| `ruff` / `ruff-format` | out of path — both in `_CORPUS_SKIP` (`run_pr_precommit.sh:110`), so the gate does not run them from this catalog |

The shared boundary was fixed once. No hook-specific exceptions were added.

## Fixed-point result

Sequence `generator → gate → generator`, run in-repo:

1. `project_llm_rules.py` → rc=0
2. `pre-commit run trailing-whitespace --all-files`
3. `project_llm_rules.py` → rc=0

No generated artifact appears in the resulting diff, and
`sync_generated_artifacts.py --force` is a no-op. A second gate execution does
not rewrite bytes the generator then changes back. **Fixed point reached.**

## Tests added

`tests/ops/test_precommit_markdown_hardbreak.py` (5 tests):

- config declares both required extensions;
- **every tracked extension that actually carries hard breaks is declared** —
  this is the guard that catches the `md`-only trap, and it fails if a future
  `.mdx`/`.markdown` source appears undeclared;
- behavioral proof per extension against the real pinned hook (hard break
  survives, single trailing space and whitespace-only line still cleaned);
- non-Markdown still loses trailing whitespace.

Verified as real guards, not tautologies: with the argument removed, 4 of 5
fail (the non-Markdown test correctly still passes).

## Validation executed

| Check | Command | Exit | Status |
|---|---|---|---|
| New regression suite | `.venv/bin/python -m pytest tests/ops/test_precommit_markdown_hardbreak.py -q` | 0 | PASS (5) |
| Guard proves itself | same, with the arg removed | 1 | PASS (4 fail as designed) |
| Full ops suite | `.venv/bin/python -m pytest tests/ops/ -q` | 0 | PASS (1134 passed, 2 skipped) |
| Hook contract | `python3 ops/scripts/validate_precommit_hook_contract.py` | 0 | PASS |
| Generated allowlist | `python3 ops/scripts/validate_generated_allowlist.py` | 0 | PASS |
| Generated sync (drift) | `python3 ops/scripts/sync_generated_artifacts.py --force --pe-manifest` | 0 | PASS (no drift) |
| Fixed point | `project_llm_rules.py` → gate → `project_llm_rules.py` | 0 | PASS |
| Consumer end-to-end | `pre-commit run trailing-whitespace --files l9-harness/MANIFEST.md` | 0 | PASS (Passed, unchanged) |
| Commit-verification contract | `python3 ops/scripts/validate_commit_verification_contract.py` | 1 | FAIL — pre-existing, see below |

`l9-harness/scripts/verify_generated.py` could **not** be run to completion in
this container: it aborts in an unrelated earlier generator,
`generate_bindings.py`, which shells `python3 -m ruff` where `ruff` is not
installed. That is an environment defect, not a code defect, and it is
`NOT_EXECUTED` rather than PASS. The manifest was therefore proven directly
instead: `update_manifest.py` regenerates `MANIFEST.md` **byte-identical** to
the gated bytes, with both hard breaks intact.

## Remaining non-blocking debt

1. **`precommit-verify-ancestry-false-positive`** (recorded via
   `session_debt.py`, left open). `validate_commit_verification_contract.py`
   fails identically on unmodified `origin/main`: `_BYPASS_TOKEN`
   substring-matches `--no-verify` inside `--no-verify-ancestry`
   (`environment/program-execution/scripts/gate_s0_baseline.py:381`), an
   argparse ancestry-probe flag, not a commit-verification bypass. Needs a
   boundary guard. All three participating files are byte-identical to `main`;
   the hook is in `_CORPUS_SKIP` so it does not gate `make pr`. Different
   defect class from this task — recorded rather than folded in silently.
2. **F3 generated-path authority (P2).** Writer file selection does not consult
   `is_generated_path()`, and that authority knows only governance paths.
   Currently unexercised. If a consumer generator is ever found emitting bytes a
   generic writer rewrites, the fix belongs at that one authority — extended to
   accept a repo-side declaration — never as a second registry.

## Final status

`CURSOR_GOVERNANCE_PRECOMMIT_BUGS_FIXED_AND_REGRESSION_PROVEN`

Valid Markdown hard breaks survive the canonical whitespace hook in both `.md`
and `.mdc`; ordinary authored-source hygiene is unchanged; generated artifacts
are no longer independently canonicalized by a generic writer; and repeated
generator/gate execution converges to one stable state. No downstream
repository was modified.
