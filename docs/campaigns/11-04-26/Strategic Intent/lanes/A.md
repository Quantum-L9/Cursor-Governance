```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/.github
  read_only:
    - https://github.com/Quantum-L9/Cursor-Governance
  unlisted_repositories: no_access
```

# Lane A | .github candidate PR + exact operator source adoption

**Objective:** Verify `.github#255` at its current head, remediate that PR inside its live changed-file set, and publish the seven-file `strategy/` overlay from the approved bytes. Lane A is the `.github` writer.

**Writable scope:** `https://github.com/Quantum-L9/.github` only. Paths are the live `#255` changed-file set plus `strategy/OPERATOR_DOCTRINE.yaml`, `strategy/operator_strategic_intent.yaml`, `strategy/alignment/**`, `strategy/ADMISSION.md`, and `strategy/OPERATOR_RELEASE_MANIFEST.json`. No path under `semantics/`. The deep `.github` clone required by `/coding-agent` is the authority root. This lane's publication checkout is a separate full clone of the same repo. Cursor-Governance is read-only.

**Entry gates:** Pin `.github` current main; fetch exact #255; independently hash every approved YAML file from its exact PR head (or if already merged, from main) against `evidence/approved_v1_exact_subject_manifest.json`; verify five-file set digest by its declared algorithm. Do not count docs staging as admission.

**Work:** Compare source and manifest digests. Repair `#255` on its existing branch when the diff stays inside its live changed-file set. Copy only the seven exact approved files into `strategy/`. If an approved source byte would have to change to get CI green, stop that file and report `CTO-BLOCKER: SUBJECT_MISMATCH`. Do not edit `semantics/`.

**Return:** CTO-STATUS: current HEAD, `#255` head, adoption branch and head, the five source digests, and `stood-down` after publish. Do not claim adopted. The CTO records adoption only after the post-integration merge train puts those bytes on main.

**Host rule:** This is the **Task-specific lane brief**, not the child system prompt. CTO renders `cto_mode.py child-prompt` from `$HOME/.cursor-governance` whose HEAD equals `origin/main`. The first child action is the rendered prompt's first action, including `/coding-agent` ACTIVE, never edits before that. All status is reported in the child transcript or Cursor Task result with CTO-STATUS / CTO-QUESTION / CTO-BLOCKER. No cross-session tool calls, no child merges, no child integration test. A repository_access header is the write list. It does not override the rendered prompt, and this pack does not quote one.

**Publication:** From the `.github` checkout run `PR_REMEDIATE=0 PR_BASE="origin/<this PR's current base>" make -C "$HOME/.cursor-governance" pr WS="<this checkout>"`. `#255` and a new adoption PR use `origin/main`. Leave `PR_STACK` empty. Then write `CTO-STATUS: stood-down`. Do not remediate, watch CI, or merge. The CTO remediates a red check inside this write set, runs integration tests, and merges this PR with the other in-scope PRs after those tests pass. A `make pr` rewrite outside this write set is named in `CTO-STATUS` and left uncommitted. No raw `git push` and no `gh pr create`.
