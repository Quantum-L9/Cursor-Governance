## Summary

<!-- One-sentence description of what this PR does. -->

## Type of Change

- [ ] Bug fix
- [ ] Feature / enhancement
- [ ] Refactor (no behavior change)
- [ ] Documentation
- [ ] CI / governance change
- [ ] Breaking change (see rollback plan below)

---

## Governance Checklist

- [ ] **Governance setup verified** — ran `setup_workspace_symlinks.sh`, symlinks resolve ([§2](https://github.com/Quantum-L9/Cursor-Governance/blob/main/CANONICAL_LAW.md#2-symlink-contract))
- [ ] **Symlinks validated** — `ls -la .cursor/rules .cursor/skills .cursor/commands` all resolve
- [ ] **All CI gates green** — no required checks failing or bypassed
- [ ] **Anti-patterns checked** — reviewed [CANONICAL_LAW.md §7](https://github.com/Quantum-L9/Cursor-Governance/blob/main/CANONICAL_LAW.md#7-anti-patterns) — none violated
- [ ] **Protected-path changes authorized** — ownership mode is `solo_ruleset` (CODEOWNERS auto-request is disabled; see `CODEOWNERS`). Protected-root rewrites carry an `ALLOW-ROOT-DELETION:` marker and pass the repo gates; CODEOWNERS review applies only when owners are re-enabled. If this PR touches any `additive_only` root file (`Makefile`, `AGENTS.md`, …), **stop** and use `.github/PULL_REQUEST_TEMPLATE/protected-root.md` (`<!-- L9_PROTECTED_ROOT_PR -->`); `make pr` injects it and CI fails without the stamp
- [ ] **Workspace wiring intact** — [§8](https://github.com/Quantum-L9/Cursor-Governance/blob/main/CANONICAL_LAW.md#8) wiring requirements satisfied
- [ ] **TRACEABILITY_MAP.yaml updated** — if this PR resolves an open unknown, mark as RESOLVED
- [ ] **Kernel ref discipline** — thin callers use `@v1`, never `@main` or bare SHA
- [ ] **L4 local autonomy** — stacked-branch local commits only during execution; no mid-execution push ([§6.2](https://github.com/Quantum-L9/Cursor-Governance/blob/main/CANONICAL_LAW.md#62-l4-local-autonomy-no-mid-execution-push))
- [ ] **Post-exec kernels** — ran `kernels/Recursive Alignment.md` then `kernels/Validate & Repair.md`; `l4_local.py authorize-release` before this PR

---

## Breaking Change

- [ ] This is a breaking change

If checked, describe the impact and migration path:

<!-- What breaks? Who is affected? How do they migrate? -->

## Rollback Plan

<!-- For blast-radius changes (health files, workflow-templates, kernel interfaces): -->
<!-- Describe the exact rollback procedure if this change causes incidents. -->

---

## Related Issues

Closes #<!-- issue number -->
