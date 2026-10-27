# Evolution Report

## Baseline

The prior Skill had strong optimize, reachability, divergence, leverage, deployment, and handoff contracts, but executed them through a mostly linear three-pass workflow.

## Evolved architecture

- Added an adaptive route across ownership, evidence state, risk, divergence, latent capability, output mode, and bottleneck class.
- Added conditional proof obligations so irrelevant gates do not consume execution budget.
- Added an evidence and decision ledger for claims, disconfirming evidence, options, probes, unknowns, final action, and convergence.
- Replaced ritual pass sequencing with highest-value unresolved proof selection under the same three-cycle ceiling.
- Added machine agreement among route, ledger, revision synthesis, optimize plan, manifest, PR body, and handoff.
- Added generated `EXECUTION_ROUTE.json`, `DECISION_LEDGER.json`, and `DECISION_RECORD.md` artifacts.
- Added manifest-level decision and proof-closure fields.
- Added deterministic routing fixtures and fail-closed negative tests.

## Preserved strengths

- Repository ownership and external-limit boundary
- Comparable performance evidence
- Bounded resources and correctness invariants
- Latent-capability reachability proof
- Documentation-code divergence disclosure
- Finding-target-option synthesis and leverage scoring
- Deploy, rollback, issue fallback, and successor-agent handoff

## Result

The Skill now spends effort according to decision value while producing a more auditable, resumable, and internally consistent PR pack.

## Full-throttle activation mode (added)

A separate, opt-in mode that enables a repository's off-by-default feature flags at scale, proves each against the repo's own tests in an isolated `git worktree`, backs out any flag that regresses tests, and packages the flip as a review-required PR (never auto-merged). It consciously relaxes Identity-Lock #1's `dormant_by_design` clause **for testing only**; the standard scan → PR-pack pipeline and its `dormant_by_design` refusal are untouched. Scripts: `flag_inventory.py`, `full_throttle.py`, `build_flag_activation_pack.py`; contract: `references/full-throttle-activation.md`.

Compensating controls (hardened across real runs on Cursor-Governance, CEG, and EIE):

- **Polarity-aware danger block-list** — never flips a flag that enables a dangerous action (delete/deploy/publish/charge/external/…) or disables a safety control (auth/tls/verify/sandbox via `disable_*`/`skip_*`/`bypass_*`); supply-chain/open-access roots (scripts, sign-up) included.
- **Context-aware sensitivity** — a generic `enabled` under a sensitive parent block (`pii`, `auth`, `security`, `retention`, …) is danger even when the leaf name is neutral.
- **Consumer reachability** — a declared-but-unread flag (`consumer_evidence=none`) is held `needs_wiring` (flipping is a no-op; it needs a wiring change, not a flip); generic leaves resolve to `unknown` for manual verification.
- **Non-runtime / infra scope** — config under `docs/`/`infra/`/`deploy/`/`helm/`/`monitoring/` and k8s/Helm deploy blocks (`ingress`/`autoscaling`/`pdb`/…) are surfaced but held, not flipped.
- **Empirical back-out + isolation + human gate** — flips are proven by the repo's own tests in a throwaway worktree; the real tree is never mutated; the PR is never auto-merged.
