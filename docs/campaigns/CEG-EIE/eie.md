You declined the coding agent for F1 and F2, so I've started nothing. CTO CEG's pre-deploy check raised two EIE findings, and I verified both are real on EIE main (a606791):

- **F1 (high): EIE sends an action Gate doesn't have.** After every enrichment, EIE sends `score-invalidate` through Gate (`app/engines/packet_router.py:1217`, called from `app/services/side_effect_coordinator.py:561`). Gate doesn't define that action and only accepts its defined actions, so every call is refused. The call doesn't wait for an answer, so the refusal only shows up in EIE's own log. My recommendation is to remove the call rather than add the action to Gate: CEG computes scores at match time from the graph, and converge results already reach the graph through the sync step.
- **F2 (medium): EIE doesn't refuse to start without a Gate key setting.** In staging and production, if `L9_GATE_SIGNING_KEY_IDS` is unset, EIE only logs an error and keeps accepting packets that claim to come from Gate (`app/middleware/gate_ingress.py` `resolve_gate_key_binding`). CEG refuses to start in the same case, and EIE should do the same.

**K2 needs you:** EIE's signing key `enrichment-engine-v1` doesn't exist yet. Gate needs its public key; the private key goes into EIE's Infisical project. Gate signs with ed25519, and EIE and the Gate SDK both support ed25519, so I'd generate an ed25519 key pair. That's a secret only you should create. Separately, CTO CEG's check lists the signing method for the other services (`hmac-sha256` or ed25519) as an open decision for you.

How do you want F1 and F2 handled?
- **Agent now:** I launch one EIE coding agent for both fixes as a single PR. It's code only, nothing deploys, so it fits the deploy hold.
- **Later:** I record both findings and wait until you clear the hold.
- **Other:** something different, for example adding `score-invalidate` to Gate instead of removing the call.

The campaign's code is all merged. What's left is two EIE fixes, deployment (on hold by your decision), and a few setup steps only you can do. No agents are running, and I've told CTO CEG that F1 and F2 are recorded and deferred.

## Done
- **EIE:**
  - #347: converge fixes.
  - #348 and #349: plasticos 0.6.0.
  - #350: removed the old health code.
  - #351: converge results sync to CEG.
  - #352: budgeted enrichment sweep.
- **Gate:** #43, #44 and #45.
- **CEG:** #494, #497 and #498.
- **Odoo:** #506 and #507 (converge v2), and #512 (sweep, merged to Staging, switched off).
- **Settled:**
  - The tenant is `plasticos` everywhere.
  - Gate's permission entries are recorded but not yet applied:
    - EIE: `enrichment-engine-v1`, health-assess and sync.
    - Odoo: `odoo-plasticos-v1`, its four actions.
  - Each CTO deploys its own repo through `l9-deploy`.

## Left: EIE code (needs a coding agent later, two fixes, about one small PR)
1. **F1 (high):** remove EIE's `score-invalidate` call through Gate.
   - Where: `app/engines/packet_router.py` `notify_score_invalidate`, called from `app/services/side_effect_coordinator.py`.
   - Why: Gate doesn't define the action, so every call is refused and only EIE's log shows it.
2. **F2 (medium):** make EIE refuse to start in staging and production when `L9_GATE_SIGNING_KEY_IDS` is unset, as CEG already does (`app/middleware/gate_ingress.py`).

## Left: EIE #353 (`l9-deploy` setup, open and unmerged)
- **Before I'd merge it:**
  - Confirm C1 (46.62.243.82) as EIE's production server, or name another.
  - Dismiss the three Scorecard "high" alerts as "won't fix": the three write permissions they flag are required for the release to work.
- **Before EIE can deploy, set up:**
  - An Infisical project `enrichment-inference-engine` with a `prod` environment, the secrets listed earlier, and read access for `l9-deploy`'s machine identity.
  - The `l9-deploy` runner's SSH key in `~actions/.ssh/authorized_keys` on C1.
  - The `eie-postgres` and `eie-redis` containers on C1's `l9-runtime` network.

## Left: keys (yours to create)
- **K2:** an ed25519 key pair for `enrichment-engine-v1`. Give the public key to CTO CEG for Gate; put the private key in Infisical.
- **Signing method:** decide what the services sign with (CTO CEG's open item F9). I recommend ed25519.

## Left: deployment (on hold until you clear testing and settings)
1. **`l9-deploy` has never completed a deploy.** Its runner fails at "uv sync", and its daily self-check fails. CTO State Node owns this. Leave run 43779221701, which is waiting for your approval, unapproved until CTO State Node says the runner works.
2. **Gate, then CEG:** CTO CEG deploys them and applies the permission entries.
3. **EIE:** merge #353, request the deploy, and you approve it.
4. **Sweep on:** set `L9_ENRICHMENT_SWEEP_ENABLED=true` in EIE's `.l9/deployment.yaml` (a reviewed change; $5 daily cap), telling CTO CEG first. Then turn on the Odoo scheduler, which is CTO Odoo's to do.

## Handoff
- **Owners:**
  - EIE: CTO EIE, this session `session_017xwbxxupo1nc2CvFZN6ewa`.
  - Gate and CEG: CTO CEG, `session_017xwbxwbZvSLdH4cB92oGzQ`.
  - `l9-deploy`: CTO State Node, `session_017xwbxusKezS2o8uzLJaSek`.
  - Odoo: CTO Odoo, `session_017xwbxuHzgYyNp8PADvkSnt`.
- **Open PRs in EIE:** #353, and #328, which you asked me to leave.
- **The sweep's contract** is `docs/contracts/enrichment-sweep.md` in the EIE repo.