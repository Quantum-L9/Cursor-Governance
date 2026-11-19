# Final integrated campaign receipt | not pre-populated

**This file is a report structure, not proof that anything executed.** LCTO fills it from current independent receipts after execution.

- Campaign ID and activation authorization / actual host mode state
- Final immutable source/authority SHA and affected scope
- Per-lane PR URL, exact head, review/CI/merge state and owner
- Actual test/CI steps and skips (false-green checks forbidden)
- Dependent releases, public artifact availability, deployments and runtime identity where applicable
- Negative controls, security boundaries, backup/restore and rollback where applicable
- Each gate with evidence link and exact final status
- Every finding disposition and residual UNKNOWN/BLOCKED with wake condition
- One minimal operator decision if external approval is genuinely still required
- Terminal verdict: COMPLETE only with all applicable evidence, otherwise BLOCKED/PARTIAL
