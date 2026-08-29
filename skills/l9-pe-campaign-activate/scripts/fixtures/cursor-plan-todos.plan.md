---
name: Claude session parity
overview: Align Claude Code SessionStart with Cursor load card and per-session skill/rule heal.
todos:
  - id: t0-isolate-baseline
    content: Create wired worktree from origin/main
    status: pending
  - id: t1-shared-renderer
    content: Add ops/hooks/render_session_state.py
    status: pending
isProject: false
kernel_pass:
  bound_path: skills/l9-pe-campaign-activate/scripts/fixtures/cursor-plan-todos.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-08-29T07:05:00Z
    body_sha256: "8a360b6c213ebf02c7cccf796aab297ee8e9acb10273512a94bfe6cf6275902a"
    deltas: ["add kernel_pass so this test fixture can land without latching precommit"]
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-08-29T07:06:00Z
    body_sha256: "8a360b6c213ebf02c7cccf796aab297ee8e9acb10273512a94bfe6cf6275902a"
    deltas: ["no material delta"]
---

# Claude SessionStart parity (A+B)

Body prose only. Work items live in frontmatter todos, not Release A blocks.
