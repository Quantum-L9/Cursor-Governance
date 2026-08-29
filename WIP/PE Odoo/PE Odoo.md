Yes. Do these only on IB-Odoo_19 PR #156 / branch fix/gate-writeback-match-converge. Do not touch EIE, CEG, or Gate_SDK during this pass.

Before editing, make sure Cursor shows that branch and that you do not have unrelated changes mixed into it. The files below are the current files I verified on that branch. 

1. Require two switches before automatic CRM writeback.
    Open:
    plasticos_gate/services/gate_config.py
    Find gate_auto_writeback_enabled(). Right now it only checks plasticos.gate.auto_writeback, so an old database containing 1 can still enable automatic writes. 
    Replace that function with:

def gate_auto_writeback_enabled(env) -> bool:
    """Return True only after explicit operator approval for live writeback.
    Two independent switches are required:
    - plasticos.gate.auto_writeback=1
    - plasticos.gate.auto_writeback_operator_approved=1
    Missing or false approval keeps Gate enrichment review-only.
    """
    icp = env["ir.config_parameter"].sudo()
    auto_writeback = (
        icp.get_param("plasticos.gate.auto_writeback", "0") or ""
    ).strip() in _TRUTHY
    operator_approved = (
        icp.get_param(
            "plasticos.gate.auto_writeback_operator_approved",
            "0",
        )
        or ""
    ).strip() in _TRUTHY
    return auto_writeback and operator_approved

    The important part is:

return auto_writeback and operator_approved

    That gives you these semantics:

auto_writeback=0, approval=0  -> review only
auto_writeback=0, approval=1  -> review only
auto_writeback=1, approval=0  -> review only
auto_writeback=1, approval=1  -> automatic writeback

    So an old database with only auto_writeback=1 becomes safe automatically because the new approval key is absent and therefore evaluates false. The existing code currently has only the first test. 
2. Add the new approval configuration key.
    Open:
    plasticos_gate/data/gate_icp_seed.xml
    Find the existing record:

<record id="param_gate_auto_writeback" model="ir.config_parameter">
    <field name="key">plasticos.gate.auto_writeback</field>
    <field name="value">0</field>
</record>

    Immediately after it, add:

<record id="param_gate_auto_writeback_operator_approved" model="ir.config_parameter">
    <field name="key">plasticos.gate.auto_writeback_operator_approved</field>
    <field name="value">0</field>
</record>

    Do not change the existing auto_writeback default back to 1.
    Your file already uses the same design for plasticos.gate.field_family_cutover_operator_approved, so this is consistent with the repository’s existing safety pattern. The entire XML file is under noupdate="1". 
    Also note why step 1 matters more than the XML seed: we are not relying on the XML to overwrite existing databases. The Python function fails closed when the approval parameter does not exist.
3. Make EIE responses and CEG candidates fail closed.
    Open:
    plasticos_gate/services/gate_mappers.py
    There are two changes.
    First, find this line in map_converge_response():

state = payload.get("state", EIE_STATE_COMPLETED)

    Replace it with:

state = payload.get("state")

    Leave the following status expression essentially as-is:

failure_reason = payload.get("failure_reason")
status = (
    "ok"
    if state == EIE_STATE_COMPLETED and not failure_reason
    else (failure_reason or state or "failed")
)

    The current code invents "completed" when EIE did not send a state. That’s exactly what we’re removing. The ConvergeResponse.state field is already nullable, so None is valid internally. 
    Second, in map_match_response(), locate the candidate loop. Right now every candidate with a resolvable entity_ref gets appended, even though the object stores eligible=False. 
    After successful buyer_partner_id resolution and before constructing MatchCandidate, insert:

if cand.get("eligible") is not True:
    continue

    So that portion becomes conceptually:

for cand in candidates:
    entity_ref = cand.get("entity_ref")
    try:
        buyer_partner_id = resolve_buyer_partner_id(entity_ref)
    except UnresolvableBuyerRef as exc:
        unresolved.append(
            {
                "entity_ref": entity_ref,
                "reason": str(exc),
            }
        )
        continue
    if cand.get("eligible") is not True:
        continue
    failed_gates = cand.get("failed_gates") or []
    # existing MatchCandidate construction follows

    Use is not True, not merely if not cand.get("eligible"), because the invariant we want is explicit:
    only a literal positive eligibility decision becomes actionable.
    Missing eligibility therefore fails closed too.
4. Make the existing Inject button approve a stored Gate proposal.
    Open:
    plasticos_enrichment/models/enrichment_run.py
    The current action_inject() immediately enters the old extraction_ids → material profile workflow. It has no Gate branch even though Gate proposals are stored on the run in gate_proposal. 
    Do not delete the old path in this PR.
    Add a Gate branch immediately after the current state validation:

self.ensure_one()
if self.state not in ("validated", "review"):
    raise UserError(
        "Run must be validated or manually approved from review.",
    )
if self.engine_used == "gate":
    if self.state != "review":
        raise UserError(
            _("Gate enrichment can only be manually injected from review state.")
        )
    proposal = self.gate_proposal or {}
    proposed = proposal.get("proposed_partner_fields") or {}
    if not isinstance(proposed, dict) or not proposed:
        raise UserError(
            _("Gate proposal contains no partner fields to approve.")
        )
    audit = {
        "gate_packet_id": self.gate_packet_id,
        "gate_correlation_id": self.gate_correlation_id,
    }
    written = self._apply_converge_writeback(proposed, audit)
    if not written:
        raise UserError(
            _(
                "Gate proposal did not write any fields. "
                "The proposed fields were either not allowed or already populated."
            )
        )
    self.write(
        {
            "state": "injected",
            "injected_at": fields.Datetime.now(),
            "fields_written": written,
            "validation_issues": False,
        }
    )
    self.message_post(
        body=(
            f"Gate converge proposal manually approved: "
            f"{written} partner field(s) written "
            f"(packet {self.gate_packet_id or ''})."
        ),
        subtype_xmlid=SUBTYPE_NOTE,
    )
    return True
# existing non-Gate injection code continues below here
svc = self.env["plasticos.enrichment.service"]

    That early return True is important. It prevents Gate enrichment from falling through into the retired/local material-extraction workflow.
    The flow then becomes:

Gate returns EIE result
        ↓
Odoo stores gate_proposal
        ↓
state = review
        ↓
operator clicks Inject
        ↓
action_inject sees engine_used == "gate"
        ↓
revalidates proposal
        ↓
writes allowed empty res.partner fields
        ↓
state = injected

    The existing run already stores gate_proposal, gate_packet_id, and gate_correlation_id, so you do not need a new model or UI button. 
5. Re-enforce the allowlist at the actual database-write boundary.
    Still in:
    plasticos_enrichment/models/enrichment_run.py
    Find:

def _apply_converge_writeback(self, proposed, audit):

    Today this function only asks whether a field exists on res.partner and whether the field is empty. That means a manipulated/stale stored gate_proposal could contain another valid partner field and bypass the earlier proposal-builder allowlist. 
    Add the allowlist import inside the function:

from odoo.addons.plasticos_gate.services.gate_allowlists import (
    PARTNER_WRITEBACK_FIELD_ALLOWLIST,
)

    Then make the beginning of the function:

def _apply_converge_writeback(self, proposed, audit):
    """Backfill allowlisted partner fields (merge-not-overwrite) with provenance."""
    from odoo.addons.plasticos_gate.services.gate_allowlists import (
        PARTNER_WRITEBACK_FIELD_ALLOWLIST,
    )
    partner = self.partner_id
    to_write = {}
    for field_name, value in (proposed or {}).items():
        if field_name not in PARTNER_WRITEBACK_FIELD_ALLOWLIST:
            continue
        if field_name not in partner._fields:
            continue
        if value in (None, False, ""):
            continue
        if partner[field_name]:
            # merge-not-overwrite: never clobber existing values
            continue
        to_write[field_name] = value
    if not to_write:
        return 0
    partner.write(to_write)
    # existing provenance logic continues unchanged

    The current canonical allowlist is:

name
website
city
zip
street
street2
email
phone

    It lives in plasticos_gate/services/gate_allowlists.py. 
    This gives you defense in depth:

EIE fields
   ↓
proposal builder allowlist
   ↓
stored gate_proposal
   ↓
operator approval
   ↓
FINAL WRITEBOUNDARY ALLOWLIST  ← step 5
   ↓
res.partner.write()

6. Update the tests so they test the new behavior, not the old assumptions.
    Start with:
    tests/test_gate_match_contract.py
    The current test literally asserts that auto_writeback=1 by itself enables automatic writing. That must stop being true. 
    Replace:

def test_gate_auto_writeback_enabled_on_when_flag_one():
    env = _MockEnv({"plasticos.gate.auto_writeback": "1"})
    assert gate_auto_writeback_enabled(env) is True

    with these:

def test_gate_auto_writeback_requires_operator_approval():
    env = _MockEnv(
        {
            "plasticos.gate.auto_writeback": "1",
        }
    )
    assert gate_auto_writeback_enabled(env) is False
def test_gate_auto_writeback_enabled_when_both_flags_one():
    env = _MockEnv(
        {
            "plasticos.gate.auto_writeback": "1",
            "plasticos.gate.auto_writeback_operator_approved": "1",
        }
    )
    assert gate_auto_writeback_enabled(env) is True
def test_gate_auto_writeback_disabled_when_operator_approval_zero():
    env = _MockEnv(
        {
            "plasticos.gate.auto_writeback": "1",
            "plasticos.gate.auto_writeback_operator_approved": "0",
        }
    )
    assert gate_auto_writeback_enabled(env) is False

    Add a seed test:

def test_gate_icp_seed_auto_writeback_operator_approval_off():
    seed = (
        Path(__file__).resolve().parents[1]
        / "plasticos_gate/data/gate_icp_seed.xml"
    )
    text = seed.read_text(encoding="utf-8")
    block = text.split(
        'id="param_gate_auto_writeback_operator_approved"',
        1,
    )[1].split("</record>", 1)[0]
    assert '<field name="value">0</field>' in block

    Add the missing-state test:

def test_map_converge_response_missing_state_fails_closed():
    resp = map_converge_response(
        {
            "fields": {
                "website": "https://enriched.example",
            }
        }
    )
    assert resp.state is None
    assert resp.status != "ok"

    Add the eligibility test:

def test_map_match_response_excludes_ineligible_candidates():
    payload = {
        "candidates": [
            {
                "entity_ref": "res.partner:7",
                "eligible": False,
                "score": 99,
                "score_scale": "0_to_100",
                "rank": 1,
            }
        ],
        "total_candidates": 1,
    }
    mapped = map_match_response(payload)
    assert mapped.results == []
    rows = map_match_response_to_matcher_dicts(mapped)
    assert rows == []

    Also update existing positive match fixtures that currently omit eligible. For example, the sorting test currently has candidates such as:

{"entity_ref": "res.partner:1", "score": 40, ...}

    Change valid candidates to:

{
    "entity_ref": "res.partner:1",
    "eligible": True,
    "score": 40,
    "score_scale": "0_to_100",
}

    Otherwise those fixtures will correctly fail closed after step 3. The current test file already has a mix of explicit and missing eligibility fields. 
    There is an even more important runtime test file:
    plasticos_enrichment/tests/test_gate_enrichment_fallback.py
    Despite the filename, this is the real Odoo runtime suite for Gate enrichment. It is loaded by the module test mechanism. 
    Its _fake_gate_result() currently produces the old response shape:

{
    "status": "ok",
    "final_fields": {...},
}

    That test helper must be converted to canonical EIE EnrichResponse semantics:

def _fake_gate_result(
    packet_id="pkt-conv-1",
    correlation_id="corr-conv-1",
    final_fields=None,
    state="completed",
    failure_reason=None,
):
    packet = SimpleNamespace(
        header=SimpleNamespace(
            packet_id=packet_id,
            correlation_id=correlation_id,
        )
    )
    payload = {
        "state": state,
        "fields": final_fields or {
            "website": "https://enriched.example"
        },
        "failure_reason": failure_reason,
    }
    return {
        "packet": packet,
        "payload": payload,
    }

    Then change the failure test from something like:

status="error"

    to:

state="failed",
failure_reason="worker error",

    The current runtime helper is actually one reason the missing-state bug could hide: it sends neither the canonical state nor fields shape. 
    Update the live auto-writeback runtime test so it explicitly enables both switches before calling action_execute():

icp = self.env["ir.config_parameter"].sudo()
icp.set_param("plasticos.gate.auto_writeback", "1")
icp.set_param(
    "plasticos.gate.auto_writeback_operator_approved",
    "1",
)

    Then add the most important new runtime test: manual review → Inject.
    The shape should be:

def test_gate_review_proposal_can_be_manually_injected(self):
    icp = self.env["ir.config_parameter"].sudo()
    icp.set_param("plasticos.gate.auto_writeback", "1")
    icp.set_param(
        "plasticos.gate.auto_writeback_operator_approved",
        "0",
    )
    partner = self._new_partner()
    run = self._new_run(partner)
    with (
        patch(_CLASSIFY, return_value=_available_verdict()),
        patch(_ENABLED, return_value=True),
        patch(
            _SEND,
            return_value=_fake_gate_result(
                final_fields={
                    "website": "https://enriched.example",
                    "city": "Raleigh",
                }
            ),
        ),
    ):
        run.action_execute()
    self.assertEqual(run.state, "review")
    self.assertFalse(partner.website)
    self.assertFalse(partner.city)
    run.action_inject()
    self.assertEqual(run.state, "injected")
    self.assertEqual(run.fields_written, 2)
    self.assertEqual(
        partner.website,
        "https://enriched.example",
    )
    self.assertEqual(partner.city, "Raleigh")

    I would also add one defense-in-depth assertion by tampering the stored proposal before Inject with a field such as comment, which exists on res.partner but is not in the writeback allowlist. After action_inject(), partner.comment must remain empty. The current allowlist intentionally excludes comment. 
7. Bump both Odoo module versions after the behavior is changed.
    Open:
    plasticos_gate/__manifest__.py
    Change:

"version": "19.0.1.1.0",

    to:

"version": "19.0.1.1.1",

    The current version is 19.0.1.1.0. 
    Then open:
    plasticos_enrichment/__manifest__.py
    Change:

"version": "19.0.2.0.1",

    to:

"version": "19.0.2.0.2",

    The current version is 19.0.2.0.1. 
    Do the version bumps last, after the code and tests are in place. That way the version change accurately represents the finished behavioral change rather than an unfinished intermediate state.

After all seven edits, the behavior you should be able to prove is:

Gate auto-writeback
    requires auto_writeback=1
    AND operator_approved=1
Missing EIE state
    -> never "ok"
CEG eligible=false/missing
    -> never actionable
Gate review result
    -> stored proposal
    -> no CRM mutation
Operator clicks Inject
    -> proposal revalidated
    -> allowlist rechecked
    -> existing partner values preserved
    -> allowed empty fields written
    -> provenance written
    -> run becomes injected
Gate_SDK
    -> unchanged
EIE
    -> unchanged
CEG
    -> unchanged

One detail I want you to pay special attention to: update plasticos_enrichment/tests/test_gate_enrichment_fallback.py to use state + fields. That runtime test is currently modeling the old response shape, and fixing only the production code without fixing that test contract would leave exactly the architectural ambiguity we just spent time resolving. 