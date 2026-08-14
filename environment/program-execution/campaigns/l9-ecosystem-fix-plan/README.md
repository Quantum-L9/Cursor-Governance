# Campaign: l9-ecosystem-fix-plan

Registration of the **L9 Ecosystem Low-Hanging-Fruit Fix Campaign** in the
governance SSOT, per the campaign source's `intended_drop_path`.

| Artifact | Purpose |
|---|---|
| `CAMPAIGN_SOURCE.yaml` | Immutable operator-intent seed (`l9.program-execution.campaign-source.v2`). sha256 `158e26c7a72176347eb2a62754b499d6387a45b988f835faacdb1f30590a9847`. |
| `source-integrity-receipt.json` | Digest binding of the source (matches the pack's recorded digest). |
| `handoff/CAMPAIGN_HANDOFF.md` | Human-readable controller handoff + AUTH-001 approval packet. |
| `handoff/handoff.json` | Schema-valid `program-execution-controller.handoff-receipt.v2`. |
| `deliverables/ib-odoo_19/` | Hand-off for the out-of-scope `cryptoxdog/IB-Odoo_19` target (TASK-004 match mapper + TASK-006 converge mapping) that could not be pushed to that repo. |

## Outcome (owner terminal verdict: CONVERGED)

- **Admission locked** — TASK-001 COMPLETED, GATE-001 PASS.
- **Reachable engineering landed as reviewable PRs** (bounded, reversible, feature-gated):
  - EIE — [Quantum-L9/Enrichment.Inference.Engine#166](https://github.com/Quantum-L9/Enrichment.Inference.Engine/pull/166)
  - CEG — [Quantum-L9/Cognitive.Engine.Graphs#195](https://github.com/Quantum-L9/Cognitive.Engine.Graphs/pull/195)
- **DEC-001** accepted → OPTION-B (candidate identity is the namespaced `entity_ref`).
- **Blocked** — `cryptoxdog/IB-Odoo_19` is out of scope / unreachable; TASK-002 (Odoo half),
  TASK-004, TASK-006, and the Wave-6 round-trips remain unexecuted. Their design is delivered
  under `deliverables/ib-odoo_19/` for manual application (or attach the repo and re-run).

## Note on scope of this registration

Per **DNB-003**, mutable controller runtime state (the instantiated blueprint/controller pair,
SQLite ledger, per-run workspaces, receipts) is intentionally **NOT** committed here — it lives
under the external program root `$HOME/.l9/programs/l9-ecosystem-fix-plan`. Only the immutable
source, closeout receipts, and the Odoo hand-off deliverable are registered in the SSOT.

_AUTH-001 declared owner terminal verdict CONVERGED and expanded this campaign's
authorization ceiling to commit/push/pull_request. Merge remains denied. The
controller still only recommends; IB-Odoo_19 waves remain blocked on target
binding._
