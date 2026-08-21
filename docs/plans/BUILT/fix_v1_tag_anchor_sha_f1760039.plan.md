---
name: Fix v1 tag anchor SHA
overview: "Fix a genuine upstream defect discovered while auditing `core_v2_org_delivery`: the `Quantum-L9/.github` repo's `ops/tag-v1.sh` script hardcodes the wrong `EXPECTED_SHA` for cutting the immutable `v1.0.0` / moving `v1` tags on `Quantum-L9/l9-ci-core`. If run as-is, it would permanently freeze a supply-chain security regression (unpinned, floating third-party GitHub Actions, including `scorecard-action`) into an \"immutable\" release tag. This plan corrects the anchor and adds a verification script the human runs before pushing the tag. PyPI publishing is explicitly out of scope per prior clarification."
todos:
  - id: phase0-baseline
    content: Clone Quantum-L9/.github to scratch dir; capture baseline tag-v1.sh and confirm no v1/v1.0.0 tag exists yet
    status: completed
  - id: phase1-fix-anchor
    content: Update EXPECTED_SHA in ops/tag-v1.sh from 2b330a5... to 2a3270be5...; add provenance comment
    status: completed
  - id: phase2-verify-script
    content: "Write ops/verify-v1-anchor.sh: enumerate uses: lines at EXPECTED_SHA, assert 40-char SHA pins, allowlist the megalinter dynamic-flavor exception"
    status: completed
  - id: phase3-validate
    content: Run verify script against new anchor (expect PASS) and old anchor (expect FAIL, proving detection works)
    status: completed
  - id: phase4-docs
    content: Write PR description explaining the divergent-branch finding; optionally footnote AGENTS.md Legacy @v1 section in l9-ci-core
    status: completed
  - id: phase5-pr
    content: Open PR against Quantum-L9/.github; human reviews/merges and later runs verify+tag scripts manually
    status: completed
isProject: false
---

## The defect (verified against the live repos)

`Quantum-L9/.github`'s `ops/tag-v1.sh` hardcodes:

```bash
EXPECTED_SHA="2b330a5aab90cd7781bef08f14c5e7904b61bc56"
```

This is the SHA the script will `git checkout`, tag as immutable `v1.0.0`, and force-move the `v1` moving tag to, on `Quantum-L9/l9-ci-core`. Consumers pin against `@v1` / `@v1.0.0`.

**The problem:** `2b330a5` sits on a branch of `l9-ci-core`'s history that diverged from `main` *before* PR #8 (commit `8928005`) landed the SHA-pinning hardening fix. At `2b330a5`, every workflow, including `.github/workflows/scorecard.yml`, still references third-party actions by floating/mutable tag:

```yaml
- uses: actions/checkout@v6
- uses: ossf/scorecard-action@v2
- uses: github/codeql-action/upload-sarif@v4
```

Cutting `v1.0.0` at this SHA would permanently bake a mutable-tag supply-chain weakness into a tag whose entire purpose is immutability. This is the "scorecard-action ref" defect the user originally flagged — it is a symptom of the wrong anchor SHA, not a standalone typo in `scorecard.yml` itself.

**Verified correct anchor:** `2a3270be5f5184099c33a101807f65b1becf4e7c` — confirmed by direct inspection to be the immediate parent of the v2-rewrite commit (`git show -s --format=%P 54a2f2f...` → `2a3270be5...`), i.e. the last commit of the pre-v2-rewrite v1 lineage. At this SHA:
- Same 9 `.github/workflows/*.yml` files exist as at `2b330a5` (`git diff` of the two file listings is empty — no kernel added/removed, so the tag's existing message "8 workflow_call kernels (pr-pipeline, release-publish, nightly, pre-commit-ci, trio-governance, security, scorecard, sbom)" stays accurate).
- `scorecard.yml` is fully SHA-pinned: `actions/checkout@df4cb1c...`, `ossf/scorecard-action@4eaacf0...`, `github/codeql-action/upload-sarif@8aad20d...`.
- Every *static* third-party `uses:` line across all 9 files is SHA-pinned, **except** one pre-existing, unrelated pattern: `pr-pipeline.yml`'s advisory MegaLinter step uses a runtime-computed path `uses: oxsecurity/megalinter/flavors/${{ steps.flavor.outputs.flavor }}@v8` (the flavor is resolved from a prior step's output, so it cannot be a static SHA pin). This is not new debt introduced by this plan and is out of scope for this fix — it must be explicitly allow-listed in the verification script (Phase 2), not silently ignored.
- No `.github/actions/` composite actions exist yet at this SHA (added later, post-v2-rewrite) — nothing else to audit.

**No tag pushed yet:** `git ls-remote --tags origin` on `l9-ci-core` shows no `v1` or `v1.0.0` tag exists. This is a **preventive** fix — no retag/rollback needed, just correct the script before anyone runs it.

**Repo boundary:** the defect and its fix live entirely in `Quantum-L9/.github` (`ops/tag-v1.sh`), a separate repo from `Quantum-L9/l9-ci-core` (the current workspace). It is not locally cloned. No content changes are required inside `l9-ci-core` itself; only an optional documentation footnote in [AGENTS.md](AGENTS.md) (`## 6. Legacy @v1` section) for discoverability from this repo.

**Explicitly out of scope (per prior clarification):** publishing `l9-ci` to PyPI. Not touched by this plan.

---

## Build plan

### Phase 0 — Baseline (in a scratch clone of `Quantum-L9/.github`, outside this workspace)

- Clone `Quantum-L9/.github` to a temporary directory (this workspace only holds `l9-ci-core`).
- Record baseline: current `ops/tag-v1.sh` contents/blob SHA, current `main` HEAD of `.github`.
- Re-confirm (from within that clone, against `l9-ci-core`) that no `v1`/`v1.0.0` tag exists yet — abort/re-scope if one has appeared since this research.

### Phase 1 — Correct the anchor in `ops/tag-v1.sh`

- Change `EXPECTED_SHA="2b330a5aab90cd7781bef08f14c5e7904b61bc56"` → `EXPECTED_SHA="2a3270be5f5184099c33a101807f65b1becf4e7c"`.
- Add an inline comment directly above the constant recording *why*: last pre-v2-rewrite commit (direct parent of v2 rewrite `54a2f2f`); supersedes the originally-planned `2b330a5`, which predated the Actions SHA-pinning hardening (PR #8 / `8928005`) and would have frozen floating `scorecard-action`/`checkout`/`codeql-action` refs into the immutable tag.
- Leave the tag message and kernel list as-is (verified accurate at the new SHA) but append a short clause noting all static third-party actions are SHA-pinned at this anchor.

### Phase 2 — Add a lightweight pre-push verification script

New file `ops/verify-v1-anchor.sh` in `Quantum-L9/.github` (sibling to `tag-v1.sh`), run manually by the human **before** `tag-v1.sh`:

- Reads `EXPECTED_SHA` (parse it out of `tag-v1.sh` rather than duplicating the literal, so the two files can never drift).
- Fetches/checks out that SHA's tree from `l9-ci-core` (read-only; no working-tree mutation required — use `git show/ls-tree` against a fetched ref, not a full checkout).
- Enumerates every `uses:` line in `.github/workflows/*.yml` at that SHA.
- For each third-party (non-local) action reference, asserts the ref after `@` is a 40-character hex SHA.
- Contains one explicit, commented allowlist entry for the known `pr-pipeline.yml` dynamic MegaLinter flavor line (`oxsecurity/megalinter/flavors/${{ ... }}@v8`), with a one-line justification, so it doesn't produce a false failure.
- Any other floating tag/branch/short-SHA found → non-zero exit, prints the offending file:line and ref.
- On success, prints a clear PASS summary: resolved SHA, file count, kernel count, "0 unpinned refs (1 documented exception)".
- `tag-v1.sh`'s header comment gets a one-line addition: "Run `ops/verify-v1-anchor.sh` first."

### Phase 3 — Validation (proves the fix and the detector both work)

- Run `ops/verify-v1-anchor.sh` against the corrected anchor `2a3270be5...` → expect PASS.
- Run it against the old, wrong anchor `2b330a5...` as a negative control → expect FAIL, listing the floating `scorecard-action@v2`, `checkout@v6`, `codeql-action@v4` (and others) — this proves the script actually detects the exact defect it exists to catch.
- Dry-run the relevant portion of `tag-v1.sh` (the `git fetch` + SHA compare, without executing tag/push) to confirm the corrected `EXPECTED_SHA` now correctly matches when checked out against the real anchor.

### Phase 4 — Documentation

- In `Quantum-L9/.github`'s PR description: explain the divergent-branch discovery (`2b330a5` vs `8928005` vs `2a3270be5`), why no retag is needed (nothing tagged yet), and link the verification script's negative-control output as proof.
- Optional, in this repo: append a short footnote to [AGENTS.md](AGENTS.md) section `## 6. Legacy @v1` recording the anchor SHA and one-line provenance, so anyone reading `l9-ci-core`'s own docs can see which historical commit `v1`/`v1.0.0` resolve to, without needing to open the sibling `.github` repo.

### Phase 5 — PR and human-run tagging

- Open a PR against `Quantum-L9/.github` containing the `ops/tag-v1.sh` edit and new `ops/verify-v1-anchor.sh`.
- After human review/merge: the human (not the agent) runs `ops/verify-v1-anchor.sh` then `ops/tag-v1.sh` from a clean `l9-ci-core` checkout to actually cut the tags. This final tagging/push step is explicitly human-executed, consistent with `core_v2_org_delivery`'s own `core-cut-v1` task and this workspace's no-auto-push governance — the agent prepares and verifies, the human pushes.
