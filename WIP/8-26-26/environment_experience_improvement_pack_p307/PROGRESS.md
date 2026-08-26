# Environment Experience Improvement Pack — Progress

Assessed against **main@post-#307-merge** on 2026-08-26.

**2 done · 9 partial · 25 not started** (of 36 records).

Legend — **done**: merged and verified; **partial**: merged/open progress with a named residual; **not started**: not addressed yet. Delivery: PR #304 + #305 (merged, operational parity, closed CI-007) and **PR #307 (open — CI-008/CI-009/CI-002 execution slice)**. Most records remain open.

## Next slice

**Ownership-aware writes (extend PR#307's is_tracked guard)**

PR#307 landed the is_tracked() ownership guard on ONE write site (the rule-adapter reconciler) and left the same-shape defect on the others. Finishing it is the highest-value, lowest-risk next move: it reuses the helper just shipped, is fully validatable in-repo with git fixtures, closes the biggest open P0 residual (CI-002), and folds in a P1 (CI-003) that shares the exact root cause — automation treating repository-owned or generated content as dirt.

- CI-002 residual (P0): apply is_tracked() before the remaining projection writes — claude_projection.py:422 (.mcp.json), reconcile_claude_l9_skills.py, reconcile_claude_commands.py, reconcile_claude_settings.py — and add Phase 2b (project to a non-owned sibling when the target is tracked). Verify the 8-fixture git-status-clean done_when.
- CI-003 (P1): make the Stop hook ownership-aware instead of residue-blind — do not demand pushing repository-owned or generated/untracked bootstrap artifacts (.claude/**, .mcp.json, .l9/**); classify by ownership, the same signal CI-002 now computes.
- CI-031 (P3, opportunistic): keep tracked-path/gitignore hygiene synchronized as the guard and the ignore stanzas move together.

- _Excluded from this slice:_ CI-002 Phase 2c (L9_AUTONOMY_STATE_DIR relocation) touches l4_local.py + local_execution_gate.py + make pr together — sequence it as its own change, not inside this slice.
- _Alternative slice:_ Toolchain slice — CI-009 residual (session-deps import smoke) + CI-023 (collapse variable-loading authorities into one loader) + CI-018 (local CI parity/hooks provisioning). Coherent and in-repo, but does not reuse just-shipped code and has no open P0.

| Progress | Item | P | Title | Delivered by / note |
|---|---|---|---|---|
| ✅ done | CI-007 | 0 | Replace standing breakglass environment strings with scoped expiring receipts | Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main |
| ✅ done | CI-033 | 99 | Use pipefail in push/retry helpers | Pre-existing (already COMPLETED at pack generation) |
| 🟡 partial | CI-002 | 0 | Make bootstrap projection ownership-aware and non-destructive to tracked repo content | PR#304 (Contract 1, merged) + Quantum-L9/Cursor-Governance PR#307 (open — CI-008/CI-009/CI-002 execution slice) |
| 🟡 partial | CI-004 | 0 | Regenerate bootstrap receipts on lifecycle/revision changes and re-probe degraded components | Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main |
| 🟡 partial | CI-006 | 0 | Resolve authority-sensitive environment drift at the actual source | Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main |
| 🟡 partial | CI-008 | 0 | Reconcile make pr doctrine with consumer-repository command contracts | Quantum-L9/Cursor-Governance PR#307 (open — CI-008/CI-009/CI-002 execution slice) |
| 🟡 partial | CI-009 | 0 | Establish one project interpreter/toolchain authority and verify importability before READY | Quantum-L9/Cursor-Governance PR#307 (open — CI-008/CI-009/CI-002 execution slice) |
| 🟡 partial | CI-010 | 0 | Make broker authentication and reachability diagnosable | Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main |
| 🟡 partial | CI-015 | 1 | Name and enforce the authoritative governance checkout | Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main |
| 🟡 partial | CI-016 | 1 | Make L4/release receipts resolve paths, branch, and head dynamically | Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main |
| 🟡 partial | CI-014 | 2 | Make target repository/cwd explicit for governance CLIs | Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main |
| ⬜ not started | CI-001 | 1 | Publish and enforce the real GitHub REST/GraphQL capability boundary | Owner is the Anthropic remote-session prompt (harness), not this repo. The make-pr path already falls back to REST, but the prompt wording fix is external. |
| ⬜ not started | CI-003 | 1 | Make the Stop hook ownership-aware instead of residue-blind | Stop-hook ownership-awareness: not started. |
| ⬜ not started | CI-005 | 1 | Make memory health transport-specific and continuity task-bearing | Memory health transport-specificity + continuity tasks: not started. |
| ⬜ not started | CI-012 | 1 | Gate rules and MCP config on actual surface capabilities | Not addressed by the merged work. |
| ⬜ not started | CI-013 | 1 | Preserve fail-closed destructive/staging gates while making denials actionable | Not addressed by the merged work. |
| ⬜ not started | CI-017 | 1 | Validate generated-artifact membership and report all drift in one pass | Not addressed by the merged work. |
| ⬜ not started | CI-018 | 1 | Make local CI parity and hooks first-class provisioning | Not addressed by the merged work. |
| ⬜ not started | CI-023 | 1 | Collapse variable-loading authorities into one reproducible loader contract | Not addressed by the merged work. |
| ⬜ not started | CI-011 | 2 | Bound large MCP responses with field projection/pagination | Not addressed by the merged work. |
| ⬜ not started | CI-019 | 2 | Coordinate concurrent writers on shared PR branches | Not addressed by the merged work. |
| ⬜ not started | CI-021 | 2 | Make session-experience and skill-usage logging observable | Not addressed by the merged work. |
| ⬜ not started | CI-022 | 2 | Provision or explicitly declare service-backed integration-test dependencies | Not addressed by the merged work. |
| ⬜ not started | CI-024 | 2 | Repair or remove foreign/stale bootstrap and deploy entrypoints | Not addressed by the merged work. |
| ⬜ not started | CI-025 | 2 | Provide sanctioned cleanup of generated/cache residue | Not addressed by the merged work. |
| ⬜ not started | CI-028 | 2 | Improve dependency provisioning evidence and determinism | Not addressed by the merged work. |
| ⬜ not started | CI-020 | 3 | Expose notification age when queued state is delivered | Not addressed by the merged work. |
| ⬜ not started | CI-026 | 3 | Support safe on-disk aliases for dot-prefixed repositories | Not addressed by the merged work. |
| ⬜ not started | CI-027 | 3 | Correct rule rationale that no longer matches container reality | Not addressed by the merged work. |
| ⬜ not started | CI-029 | 3 | Persist repeatable cross-repo E2E fixtures | Not addressed by the merged work. |
| ⬜ not started | CI-030 | 3 | Improve receipt CLI ergonomics without multiplying state owners | Not addressed by the merged work. |
| ⬜ not started | CI-031 | 3 | Keep repo documentation and tracked-path hygiene synchronized | Not addressed by the merged work. |
| ⬜ not started | CI-032 | 3 | Give slow validation units explicit headroom without weakening total proof | Not addressed by the merged work. |
| ⬜ not started | CI-100 | 4 | Investigate why PR #70's workflow runs were gated in action_required | Context-specific investigation (PR #70 action_required): not started. |
| ⬜ not started | CI-101 | 4 | Align the branch directive with the repository actually worked in | Context-specific (branch directive vs repo worked in): not started. |
| ⬜ not started | CI-102 | 4 | Valid GH_TOKEN or formal surface exemption from gh-dependent gates | Context-specific (valid GH_TOKEN / gh-gate exemption): not started. |

## Residual detail (done / partial)

### ✅ done — CI-007: Replace standing breakglass environment strings with scoped expiring receipts
- delivered_by: Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main
- residual: done_when literal 'variable absent from a fresh session': the live account still holds an inert stray L9_AUTONOMY_AUTONOMOUS_MERGE=true — delete that env line to fully satisfy it (no functional effect; the flag authorizes nothing).
- residual: KNOWN BUG (separate follow-up): the readiness merge_authority probe crashes here (runs merge_gate CLI with a non-git cwd) and false-reports 'regression'. The authority itself is correct.

### ✅ done — CI-033: Use pipefail in push/retry helpers
- delivered_by: Pre-existing (already COMPLETED at pack generation)

### 🟡 partial — CI-002: Make bootstrap projection ownership-aware and non-destructive to tracked repo content
- delivered_by: PR#304 (Contract 1, merged) + Quantum-L9/Cursor-Governance PR#307 (open — CI-008/CI-009/CI-002 execution slice)
- residual: The is_tracked guard covers only the rule-adapter reconciler (the measured 9-deletion defect). It must extend to the other write sites: claude_projection.py:422 (.mcp.json), reconcile_claude_l9_skills.py, reconcile_claude_commands.py, reconcile_claude_settings.py.
- residual: Phase 2b (project governance rules to a non-owned sibling when the target is tracked), 2c (L9_AUTONOMY_STATE_DIR outside the worktree), and 2d (per-repo gitignore propagation) are not yet built; the 8-fixture git-status-clean done_when is not yet fully verified.

### 🟡 partial — CI-004: Regenerate bootstrap receipts on lifecycle/revision changes and re-probe degraded components
- delivered_by: Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main
- residual: It is a separate receipt, not the bootstrap-state.json regenerated on container/session lifecycle; no per-component log path; stale-receipt invalidation on lifecycle not wired.

### 🟡 partial — CI-006: Resolve authority-sensitive environment drift at the actual source
- delivered_by: Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main
- residual: General mechanism (separate authority-widening drift from cosmetic drift, make repair reachable/human-only, record governing value) is not built.
- residual: done_when '0 of 33 in exactly one layer': live account still carries the inert stray var; delete it to reach the exact-one-layer end state.

### 🟡 partial — CI-008: Reconcile make pr doctrine with consumer-repository command contracts
- delivered_by: Quantum-L9/Cursor-Governance PR#307 (open — CI-008/CI-009/CI-002 execution slice)
- residual: Running the governance pre-commit config against a *consumer* workspace (cwd=$GOV, absolute --files, governance-only-local-hook skip subset) needs real-consumer validation and is scoped in-script, not enabled. The done_when's consumer-side leg is unverified.

### 🟡 partial — CI-009: Establish one project interpreter/toolchain authority and verify importability before READY
- delivered_by: Quantum-L9/Cursor-Governance PR#307 (open — CI-008/CI-009/CI-002 execution slice)
- residual: session_deps_cloud.sh still asserts 'toolchain ready' without an import smoke — the readiness dimension now catches an unimportable env, but the deps banner itself is unchanged (lower-value, cloud-only, scoped follow-up).
- residual: A sourceable scripts/env.sh (IMP-E1) was deliberately NOT added: this repo already has one interpreter authority (Makefile + ensure_gov_python.sh + gov-python prereq); a second loader would violate the one-authority goal. Container-image items (A2-A5) are external (SC-IMG): default python3 floor, distro cryptography, uv/UV_PYTHON, mypy split.

### 🟡 partial — CI-010: Make broker authentication and reachability diagnosable
- delivered_by: Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main
- residual: CONNECT cannot succeed (no platform-issued identity — external).
- residual: Broker states not fully split into proxy-denied vs upstream-error for allowlist remediation decisions.

### 🟡 partial — CI-015: Name and enforce the authoritative governance checkout
- delivered_by: Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main
- residual: done_when 'read the SSOT's issues without add_repo' is not met; non-authoritative clones are not relabeled/removed.

### 🟡 partial — CI-016: Make L4/release receipts resolve paths, branch, and head dynamically
- delivered_by: Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main
- residual: The L4/release receipt's dynamic path/branch/template resolution and stale-binding visibility (done_when: names .github/pull_request_template.md or null) were not reworked.

### 🟡 partial — CI-014: Make target repository/cwd explicit for governance CLIs
- delivered_by: Quantum-L9/Cursor-Governance PR#305 (+ predecessor PR#304), merged into main
- residual: Covers the make-target facade only; many ops/scripts governance CLIs still depend on persistent shell cwd.

