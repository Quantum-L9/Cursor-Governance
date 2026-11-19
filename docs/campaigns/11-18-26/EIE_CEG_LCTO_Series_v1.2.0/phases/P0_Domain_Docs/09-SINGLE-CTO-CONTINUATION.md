# One CTO series continuation / generated phase launch clarification

**Single activation, not five:** this phase belongs to the operator-approved parent `EIE_CEG_LCTO_Series_v1.2.0`. The embedded template-generated `00-LCTO-LAUNCH.md` contains a generic `HOLD until explicit operator activation` instruction. **Interpret that HOLD only as a prohibition on unactivated execution; it does not require a second operator activation once the parent series has been authorized and started.** The current LCTO host mode, approval ceiling and exact predecessor code-ready gate must still be verified; if host mode expires, use host-governed continuation/adoption, not a parallel unapproved CTO session.

**Phase:** P0. Requires one parent CTO activation, then P0 G0 and component sources.

Pre-rail phase readiness proves code, native tests and green PRs only. No heavy Docker until all P0-P4 PRs (including P4 E2E and DOC) have been published and green, and `P4.G_PUBLISH` passes. EIE/CEG/Gate each have their own linear stacked PR train with verified explicit parent. `make pr` remains the publication SSOT. One recurring CTO controls up to five host-governed reusable coding agents, each owns and remediates their own PR. No `Makefile` or `Repo.mk` changes, no raw push, no unauthorized merge/deploy.
