---
description: KERNEL pack / PE overlay landings use a new branch from origin/main without asking. Do not mix unrelated WIP.
---

<!-- L9_META
l9_schema: 1
origin: KERNEL_PACK_NEW_BRANCH_DEFAULT_V1
tags: [kernel, pack, git, branch, planning]
status: active
/L9_META -->

# KERNEL pack landing branch default

Do **not** ask whether to land a KERNEL pack, Program Execution overlay, or similar
governed architecture change on the current feature branch vs a new branch.

Default, without asking:

1. Create a **new branch from `origin/main`** (fast-forward-only tip) in this clone.
2. Do **not** mix unrelated WIP (legal ingest, other feature work) into that branch.
3. Ask only if the user already named the target branch as the subject of the change,
   or `origin/main` cannot be resolved.

Stock pack apply scripts that hard-reset or require a foreign `BASE_SHA` are not
the landing path in a dirty or unrelated checkout.

SSOT narrative: `AGENTS.md` section `KERNEL_PACK_NEW_BRANCH_DEFAULT_V1`.
Planning: `skills/l9-plan/references/planning-doctrine.md` law item 9.

<!-- generated-from: rules/46-kernel-pack-new-branch.mdc; do-not-edit -->
