# IB-Odoo_19 Integration Delivery — l9-ecosystem-fix campaign

**Target:** `cryptoxdog/IB-Odoo_19` · **Status:** OUT OF SESSION SCOPE — not a
Quantum-L9 repo, not attachable this session, **could not be pushed to.**
**Therefore this is a hand-off deliverable**: apply it to IB-Odoo_19 yourself (or
attach the repo in a future session and I'll open the PR directly).

This covers the two Odoo-side campaign tasks that were blocked on the unreachable
target, now fully specified against the **verified** CEG/EIE contracts and the
**resolved** DEC-001 identity decision:

- **TASK-004** — Wave 3 match mapper contract break (`results` → `candidates`) +
  DEC-001 identity mapping.
- **TASK-006** — Wave 5 converge request/response mapping (Odoo ⇄ EIE).

Reference implementations (drop-in, adapt imports to the Odoo module):
- `reference/plasticos_ceg_match_mapper.py`
- `reference/plasticos_eie_converge_mapper.py`

---

## 1. DEC-001 — candidate identity (ACCEPTED → OPTION-B)

**Decision:** CEG `candidate.entity_ref` is a **namespaced `<model>:<id>` key**
matching `^[a-z0-9_.-]+:[^\s]+$` — for Odoo buyers, `res.partner:<int>`
(e.g. `res.partner:102`). It **embeds** the `res.partner` integer but is
namespaced and tied to a `SourceRecord{system:odoo, record_ref}` mapping. It is
**NOT** a bare `res.partner` id (OPTION-A) and **NOT** a Neo4j-native node id.

**Odoo consequence:** map to `buyer_partner_id` via an **explicit resolver** that
parses the ref and accepts **only** the `res.partner` model — any other namespace
fails safe (no cross-model mis-attribution). See `resolve_buyer_partner_id()`.

**Evidence (CEG `engine/models/payloads.py`):** `ENTITY_REF_PATTERN` (l.50-51),
`MatchCandidate.entity_ref` (l.164-166), `SourceRecord{system,record_ref}`
(l.262-266); fixture `contracts/payloads/examples/match-response.json`
(`"res.partner:102"`).

> ⚠️ Residual (documented in CEG PR #195 / ADR): the **live** CEG match handler
> currently keys candidates on a bare `entity_id` node property
> (`engine/handlers.py:509,616,1497`), client-supplied at sync, **not**
> schema-defined. Until the live path is reconciled to emit the contract
> `entity_ref`, confirm which form your CEG deployment actually returns and
> adjust `resolve_buyer_partner_id()` accordingly. The resolver already fails
> safe on a bare integer (no `<model>:` prefix → skipped, never mis-mapped).

---

## 2. TASK-004 — CEG match response → Odoo buyer-match records

**The break:** the prior Odoo mapper read `payload.get("results")`. The live CEG
`/v1/execute` match response returns rows under **`candidates`** — so every
candidate was silently dropped. Fix: read `payload.get("candidates")`.

### Field mapping (CEG `MatchCandidate` → Odoo buyer-match)

| CEG contract field | Odoo target | Notes |
|---|---|---|
| `entity_ref` (`res.partner:<int>`) | `buyer_partner_id` (int) | via `resolve_buyer_partner_id()` (DEC-001) |
| `score` + `score_scale` | `normalized_score` (0–1) | `0_to_1` as-is; `0_to_100`÷100; `unnormalized_declared` left raw |
| `eligible` | `eligible` | ineligible candidates never carry a rank (contract invariant) |
| `rank` | `rank` | |
| `explanation` | `explanation` | |
| `failed_gates[]` / `feature_contributions[]` / `missing_evidence[]` | carried through | for review UI |
| response `query_id`, `direction`, `total_candidates`, `execution_time_ms`, `domain_spec_version`, `model_version`, `projection_version`, `contract_version`, `domain` | preserved verbatim | lineage |

**Do NOT** add `packet_id`/`correlation_id`/`meta` to the payload mapping — those
are transport-forbidden on CEG payloads; they live on the chassis envelope.

### VAL-004 acceptance (frozen-fixture test) — assert:
1. candidates are **not dropped** (reads `candidates`);
2. buyer ids map correctly **per DEC-001** (`res.partner:102` → `102`);
3. scores **normalize** to [0,1] per `score_scale`;
4. output **sorted descending** by normalized score;
5. a missing/invalid `entity_ref` **fails safe** (lands in `unresolved`, never a
   wrong `res.partner`).

Use the canonical CEG fixture `contracts/match_response.json` (shipped in CEG
PR #195) as the frozen input.

---

## 3. TASK-006 — Odoo ⇄ EIE converge mapping

EIE owns the `converge` action (`POST /v1/execute`). Request = `EnrichRequest`,
response = `EnrichResponse` (EIE `app/models/schemas.py`).

### Request: Odoo → EIE `EnrichRequest`

| Odoo field | EIE `EnrichRequest` | Notes |
|---|---|---|
| `entity_snapshot` | `entity` (dict, required) | Odoo `entity_id` preserved inside `entity._odoo_entity_id` (context, not a Gate transform) |
| `domain` / type | `object_type` (str, required) | |
| `objective` | `objective` (str, required) | defaults to "Full entity enrichment and inference" |
| `max_passes` | `max_variations` | **clamped 1..10** (EIE constraint) |
| `kb_context` | `kb_context` | optional — include only if provided |
| `idempotency_key` | `idempotency_key` | optional |

### Response: EIE `EnrichResponse` → Odoo (no field loss)

Carry through **all** EnrichResponse fields (`fields`, `confidence`, `state`,
`failure_reason`, `quality_tier`, `variation_count`, `pass_count`,
`consensus_threshold`, `uncertainty_score`, `processing_time_ms`,
`inference_version`, `kb_content_hash`, `kb_files_consulted`, `kb_fragment_ids`,
`inferences`, `grade_matches`, `enrichment_payload`, `feature_vector`,
`tokens_used`).

**DNB-006 (hard rule):** EnrichResponse has **no `total_cost_usd`** and converge
performs **no writeback**. The mapper marks both **explicitly UNAVAILABLE
(`None`)** — never fabricated. Cost is `tokens_used` only.

### VAL-006 acceptance — assert against a frozen/real EIE response:
- no `total_cost_usd` or writeback field is fabricated;
- no response field is lost on mapping.

Use the canonical EIE fixtures `contracts/converge_request.json` /
`converge_response.json` (shipped in EIE PR #166) as frozen I/O.

---

## 4. How to apply (since IB-Odoo_19 can't be pushed from here)

```bash
git clone https://github.com/cryptoxdog/IB-Odoo_19
cd IB-Odoo_19 && git checkout -b claude/campaign-execution-pipeline-dbc5cl
# place the two reference mappers under plasticos_gate / plasticos_matching,
# adapting imports to the Odoo module env, then:
#   - replace payload.get("results") -> the map_match_response() call
#   - wire the converge request/response through the converge mapper
# add frozen-fixture tests using CEG PR #195 + EIE PR #166 canonical fixtures
git add -A && git commit && git push -u origin HEAD   # then open a PR
```

Or **attach `cryptoxdog/IB-Odoo_19` to a session** (grant access in the Claude
GitHub settings) and I'll wire these in and open the PR directly, then run the
Wave-6 round-trip validations end to end.

---

## 5. What remains blocked until IB-Odoo_19 is reachable

- Applying/merging these mappers into IB-Odoo_19.
- Odoo Gate writeback safe-default + PR #141 install-smoke (TASK-002 Odoo half).
- The six Wave-6 launch-critical round-trip paths and six failure cases (they
  all transit Odoo). Controller verdict stays **INCONCLUSIVE** until then.

Companion artifacts: `../../handoff/CAMPAIGN_HANDOFF.md`,
`../../handoff/handoff.json`. Upstream contracts landed in **EIE PR #166** and
**CEG PR #195**.
