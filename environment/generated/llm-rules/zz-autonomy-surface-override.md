---
description: Autonomy Velocity Override — adapter surfaces outrank ask-first commit rules
---

# Autonomy Velocity Override (adapter surfaces)

When `L9_GOVERNANCE_SURFACE` is `claude-code`, `codex`, `gemini`, or `manus`
AND `L9_AUTONOMY_ENABLED=true`:

1. This override **outranks** `99-no-auto-commit` and `96-git-push-approval`
   for scoped feature-branch commit/push and PR create/update.
2. Completing reversible work MUST proceed to commit → push → PR →
   `l9-pr-remediation` without waiting for a per-action user ask.
3. Merge / force-push / hard-reset / admin-merge / secrets remain forbidden.
4. Cursor surface is unaffected (ask-first + campaign packet / `make pr`).
5. Source of truth: `ops/autonomy/surface_profile.yaml` — do not fork this text.

<!-- generated-from: ops/autonomy/surface_profile.yaml; do-not-edit -->
