---
name: meta injection pipeline
overview: "Rebuild the L9_META injector into a config-driven, portable, self-verifying pipeline: restore the two stubbed formatters behind golden fixtures, replace the hardcoded FILE_REGISTRY with path-rule resolution, make headers the source of truth via `sync --adopt`, and enforce drift with a `check` command in CI."
todos:
  - id: phase0-fixtures
    content: "Phase 0: golden fixtures + round-trip/idempotency tests per format, including the 2 legacy bare-# L9_META files, a front-matter markdown file, a .MD file, and a path containing a space"
    status: completed
  - id: phase1-formats
    content: "Phase 1: restore format_comment_block and format_python_docstring_block; extract tools/l9_meta/formats/; add legacy bare-form strip pattern, front-matter-aware markdown insertion, and delimiter-anchored detection so prose is never matched"
    status: completed
  - id: phase2-config
    content: "Phase 2: build config.py/resolve.py/discover.py (git ls-files -z, existence filter, artifacts/ exclusion); sync --adopt to generate l9-meta.yaml; ~40 rules + ~35 overrides, splitting the 11 impure path groups; delete FILE_REGISTRY and 10 ghosts; hand-review"
    status: completed
  - id: phase3-tags
    content: "Phase 3: map 188 tags to family/capability/concern facets, apply min_files floor, fold layer-restating tags, bake vocabulary into config, enforce cardinality and deterministic ordering in check"
    status: completed
  - id: phase4-schema2
    content: "Phase 4: drop owner from emitted header (verified zero consumers); parser accepts v1+v2, writer emits v2; update contracts/contract_18.yaml to schema v2 and widen scope.paths"
    status: completed
  - id: phase5-stamp
    content: "Phase 5: apply across ~615 eligible files as one isolated commit; verify check clean, all 16 front-matter files still parse, 2 legacy files have exactly one header, test-unit and contract_scanner unchanged"
    status: completed
  - id: phase6-enforce
    content: "Phase 6: add l9-meta-check pre-commit hook and CI step; update the 6 files referencing l9_meta_injector.py"
    status: completed
  - id: portability
    content: "Portability: keep tools/l9_meta_injector.py as a thin shim over tools.l9_meta.cli; implement init to scaffold l9-meta.yaml in a fresh repo"
    status: completed
isProject: false
---

# L9_META Injection Pipeline — Revision Plan (v2, evidence-corrected)

This revision re-derives every number in the prior plan from the working tree. Three claims were wrong and three high-severity hazards were missing. Corrections are marked **[CORRECTED]**; new findings **[NEW]**.

## Baseline (measured, not asserted)

Enumeration: `git ls-files -z`, filtered to files that exist on disk.

- 655 raw index entries; **620 exist on disk**. The 35-entry gap is 4 staged deletions (`chassis/app.py`, `chassis/auth/app.py`, `scripts/scripts-deploy.sh`, `tools/deploy/deploy.sh`) plus split artifacts from paths containing spaces.
- **375 files already carry a header**: 231 docstring/bare, 82 comment, 57 HTML, 5 non-standard.
- `FILE_REGISTRY` holds 245 entries; **235 exist** → 10 ghost paths.
- **Zero consumers.** Nothing outside [tools/l9_meta_injector.py](tools/l9_meta_injector.py) reads `_l9_meta`, `l9_schema`, or `owner`. The only other `L9_META` hits are files' own headers and prose.

## Corrections to the prior plan

**[CORRECTED] Blast radius of `--apply` today is 173 files, not 312.**
`main()` iterates `FILE_REGISTRY` only, never the working tree. Of the 235 existing registry entries, 173 route to a stubbed formatter (102 python, 46 yaml, 18 shell, 6 comment, 1 plain-comment) and 172 of those currently hold a real header that would be flattened. The other 62 (markdown/json/toml) use intact formatters and are safe. All damage is `git checkout`-recoverable, so this is High, not Critical.

**[CORRECTED] `owner` removal is provably safe.** With zero consumers, the contract-preservation gate passes on evidence rather than assumption. The flip side: L9_META is currently **write-only metadata**. `check` becomes its first real consumer — that is what makes the tag work worth doing, and it belongs in the plan's justification.

**[CORRECTED] Only 2 files have genuinely non-standard headers**, not 3 malformed:
- [agents/cursor/cursor_workflow_kernel.yaml](agents/cursor/cursor_workflow_kernel.yaml) — opens `# L9_META` with no `--- ... ---` delimiters
- [engine/security/llm.py](engine/security/llm.py) — same bare form, and comment-style in a `.py` file that should use docstring style

The other three (`.claude/rules/contracts.md`, `.claude/skills/pr-workflow/SKILL.md`, `contracts/contract_18.yaml`) are **prose mentions**, not headers. This is itself a requirement: a naive substring detector red-flags documentation that merely discusses L9_META, so `check` must anchor on exact delimiters or CI will fail on docs.

**[CORRECTED] Duplicate-header hazard.** `STRIP_COMMENT_META` requires `#\s*---\s*L9_META`. The bare `# L9_META` form in those 2 files will not match, so re-injection **appends a second header** rather than replacing. Needs a legacy-form strip pattern plus a fixture.

## New hazards the prior plan missed

**[NEW] Front-matter collision — highest severity.** 16 markdown files lead with YAML front matter and **none** currently carry a header:

| Group | Front-matter key | Breaks if header goes first |
|---|---|---|
| `.claude/agents/*.md` (2) | `name:` | agent discovery |
| `.claude/rules/*.md` (7) | `paths:` | rule auto-loading |
| `.claude/skills/*/SKILL.md` (5) | `name:`, `description:` | skill discovery |
| [agents/cursor/README.md](agents/cursor/README.md), [agents/cursor/docs/PRODUCTION-SPEED-PACK.md](agents/cursor/docs/PRODUCTION-SPEED-PACK.md) | `dora:` / Suite-6 header | tooling that parses them |

`inject_markdown` writes at byte 0, pushing `---` off line 1. Phase 5 as previously written would silently break Claude Code skill, agent, and rule loading in this repo. **Decision: insert after the front-matter block.**

**[NEW] `artifacts/` is generator output.** `audit_report.md`, `coverage_report.md`, `harness_report.md`, `coverage_matrix.json`, `spec_checklist.json` are produced by the audit harness. Injecting there guarantees churn on every run. **Decision: excluded.** Eligible set becomes ~615.

**[NEW] Paths with spaces.** 14 tracked paths contain spaces (`docs/ACTION ITEMS.MD`, `docs/PlasticOS Graph Cognitive Engine.yaml`, `engine/packet/README-Packet Envelope.md`, …), and one uses an uppercase `.MD` extension. Enumeration must be `git ls-files -z` with null splitting; a naive `.split()` or `*.md` glob silently drops them. `_detect_filetype` already lowercases the suffix, so `.MD` resolves correctly once enumerated.

**[NEW] Phase 2 feasibility is 86%, not "~15 overrides".** Grouping the 245 registry entries by their first two path segments yields 40 groups; 29 are layer-pure. A majority-layer-per-group rule covers 210/245 → **~35 overrides required**. Impure groups are named and must be split by rule, not by override: `tools/auditors` (audit vs tools), `engine/compliance` (config vs compliance), `engine/packet` (config vs docs), `.github/workflows` (ci vs ci+governance), and repo root (9 distinct layers across ~22 files — root needs per-file rules).

**[NEW] Coexisting metadata systems.** [.cursor/rules/25-python-dora-header.mdc](.cursor/rules/25-python-dora-header.mdc) mandates `__footer_meta__` + `__l9_trace__` for Python. Actual usage: 5 files, all under `agents/cursor/`, **zero in `engine/`**. Not a repo-wide conflict; document coexistence, do not reconcile.

**[NEW] Descoped as NotApplicable.** Zero CRLF files, zero BOM files across all 620. The only 2 files without a trailing newline are in the now-excluded `artifacts/`. Encoding-preservation work is dropped from the plan.

## Target design

```
tools/l9_meta/
  __init__.py
  model.py      # MetaRecord (schema v2, no owner); parse/serialize
  formats/      # comment.py, docstring.py, html.py, json.py, toml.py
                #   each: detect() -> bool, parse(text), render(rec), inject(text, rec)
  config.py     # loads l9-meta.yaml: vocabulary, path rules, overrides, exclusions
  resolve.py    # path -> MetaRecord via rule precedence
  discover.py   # git ls-files -z, existence filter, exclusion filter
  cli.py        # check | apply | sync | report | init
tools/l9_meta_injector.py   # thin shim -> tools.l9_meta.cli (preserves 6 doc references)
l9-meta.yaml                # per-repo SSOT
```

Resolution precedence, most specific wins: `overrides[exact path]` → `rules[]` last-match → `defaults`. Rendering is deterministic: facet order is `family, capability, concern`; within a facet, sorted. Non-deterministic ordering would churn the diff on every run.

## Phases

### Phase 0 — Golden fixtures (no production edits)
Round-trip and idempotency tests per format: `render → parse → render` is stable, and `inject(inject(x)) == inject(x)`. Must include the two legacy bare-`# L9_META` files, a front-matter markdown file, a `.MD` file, and a path with a space. This gates every later phase.

### Phase 1 — Restore formatters
Fix `format_comment_block` and `format_python_docstring_block` in [tools/l9_meta_injector.py](tools/l9_meta_injector.py) (both currently return only a prefix), mirroring `format_html_comment`. Extract into `formats/`. Add: legacy bare-form strip pattern; front-matter-aware markdown insertion; anchored (delimiter-exact) detection so prose never registers as a header.

### Phase 2 — Config resolver
`sync --adopt` reads the 375 on-disk headers plus the 245 registry entries and emits `l9-meta.yaml`. Collapse to ~40 path rules + ~35 overrides, splitting the 11 impure groups above. Delete `FILE_REGISTRY` and the 10 ghost paths. Hand-review the rule set — this is the one step that cannot be fully automated.

**Evidence caveat:** rule quality is derived from the 245 registry entries and 375 headers. The remaining ~240 unheadered files have no prior layer assignment; their values are inferred from path rules and need review at Phase 5, not blind acceptance.

### Phase 3 — Tag facets
Map the current 188 tags (112 used exactly once) to `[family, capability, concern?]`. Apply a `min_files` floor, fold tags that merely restate `layer` or the path, bake the vocabulary into `l9-meta.yaml`, and enforce cardinality in `check`.

### Phase 4 — Schema v2
Drop `owner` from the emitted header. Parser accepts v1 and v2; writer emits v2 only. Update [contracts/contract_18.yaml](contracts/contract_18.yaml) postcondition to `schema v2` and widen `scope.paths`.

### Phase 5 — Full stamp
Apply across the ~615 eligible files as one isolated commit with no other changes. Verify `check` is clean, then spot-verify: all 16 front-matter files still parse, the 2 legacy-form files have exactly one header, `make test-unit` and `python tools/contract_scanner.py` still pass.

### Phase 6 — Enforce
Add `l9-meta-check` to [.pre-commit-config.yaml](.pre-commit-config.yaml) and CI. Update the 6 files referencing `l9_meta_injector.py`: [.claude/rules/contracts.md](.claude/rules/contracts.md), [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md), [docs/AI_AGENT_REVIEW_CHECKLIST.md](docs/AI_AGENT_REVIEW_CHECKLIST.md), [agents/cursor/cursor_workflow_kernel.yaml](agents/cursor/cursor_workflow_kernel.yaml), [.cursorrules](.cursorrules), [tools/l9_template_manifest.yaml](tools/l9_template_manifest.yaml).

## Gates

Each phase closes only on evidence, reported as Passed / Failed / Skipped / NotApplicable / Unknown.

- **P1** — every format round-trips; both legacy files yield exactly one header; front-matter files keep `---` on line 1
- **P2** — `resolve()` reproduces all 375 existing headers except intentional, listed diffs
- **P4** — no consumer regression (verified: zero consumers exist)
- **P5** — `check` exits 0; test suite and contract scanner unchanged from baseline
- **P6** — a deliberately corrupted header fails pre-commit

## Known unknowns

- The ~240 currently-unheadered files have no ground-truth layer; Phase 2 rules assign values that need human review.
- `tests/fixtures/payloads/*.json` carry a `$schema` key. No Python test loads them, so runtime risk is low, but whether that schema sets `additionalProperties: false` is unverified — injecting `_l9_meta` could fail external validation.
- Whether `.claude/rules/*.md` front matter tolerates a trailing HTML comment is untested; Phase 0 fixture must confirm before Phase 5.