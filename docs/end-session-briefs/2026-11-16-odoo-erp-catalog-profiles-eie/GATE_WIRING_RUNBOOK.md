# Cursor handoff: wire Odoo.sh Staging and Production to Constellation.Gate over SSH

> **Status at campaign close (2026-11-16).** This is the runbook as issued, with SSH
> hostnames removed.
>
> - P0 returned verdict **M3** on both hosts: there is no build-persistent process
>   environment.
> - P1 is done: the public key for `odoo-plasticos-v1` is recorded with CTO CEG.
> - Gate G1 now holds: Production `93c34c6` contains `0445b30`.
> - Phases P2–P5 are blocked by M3 (an ADR is needed, see `SESSION_BRIEF.md` §3) and
>   by the operator's deferral of the Gate deploy.
> - Re-issue to Cursor only after both are cleared and `GATE_URL`, `GATE_KEY_ID` and
>   `GATE_PUBLIC_KEY` are filled in. P2's mechanism must be replaced by the one the
>   ADR picks.

## MANIFEST

- Repo: `cryptoxdog/IB-Odoo_19`. Staging = `0445b30` (#509 and #512 merged 2026-11-15).
- Hosts (SSH, from Odoo.sh → Branches → <branch> → latest build → SSH tab):
  - Staging: `<from Odoo.sh → Branches → branch → SSH tab>`
  - Production: `<from Odoo.sh → Branches → branch → SSH tab>`
- Owner: Odoo CTO session `session_017xwbxuHzgYyNp8PADvkSnt`.
- Operator authority for this runbook: Staging and Production. Production is touched only in phases P2 and P4, and
  only after promotion (gate G1 below).
- Authorities: `docs/GATE_ODOO_WIRING.md` (§1 keys, §2b parameters, §2c environment, §4 smoke checks),
  `plasticos_gate/services/gate_config.py`, `plasticos_gate/data/gate_icp_seed.xml`.

## APPROVED VALUES (operator approval 2026-11-15: "approve")

```
TENANT_PRODUCTION = plasticos
TENANT_STAGING    = plasticos
KEY_ID_PRODUCTION = odoo-plasticos-v1
KEY_ID_STAGING    = none          # Staging is NOT wired to Gate (operator decision 2026-11-15, option A)
GATE_URL          = <unset>       # from CTO CEG; proposed https://gate.quantumaipartners.com (single production Gate on C1)
GATE_KEY_ID       = <unset>       # from CTO CEG
GATE_PUBLIC_KEY   = <unset>       # from CTO CEG; public, not a secret
```

**If any value you need for a phase reads `<unset>`, do not run that phase.** Phases P0 and P1 need none of them.
The tenant is fixed by the engines, not chosen. EIE (EIE-IDENT-02) and CEG (HEALTH-05) both bind tenant id = domain
spec id = Neo4j database name, and the only PlasticOS domain is `plasticos`. Any other tenant is refused. This
overrides `scrapmanagement` in `docs/GATE_ODOO_WIRING.md`.
Never invent a value.

**Topology (operator decision 2026-11-15, option A).** There will be one Gate, the production Gate on C1. Only
Production Odoo gets a key and the Gate environment, so only Production reaches EIE and CEG. Staging Odoo gets no key,
no `GATE_URL` and no `L9_*` variables, because with the shared tenant `plasticos` it would otherwise touch production
engine data and the sweep budget. Staging gets wired only when a separate staging Gate (with staging EIE/CEG) exists.
Gate itself is not deployed yet: P2 and P5 wait for CTO CEG.

## OBJECTIVE

Odoo calls EIE (`converge`, `enrichment-sweep`, `enrichment-sweep-results`) and CEG (`match`) only through Gate,
with no hand-typed configuration by the operator:

1. Find out how process environment variables persist on Odoo.sh builds (P0, read only).
2. Generate Production's ed25519 key pair on this workstation. Hand back only the public half (P1).
3. Install Odoo's Gate environment on the **Production** build through the mechanism P0 proved (P2).
4. Set the Odoo System Parameters on each database (P3 Staging, P4 Production).
5. Run smoke checks on Production (P5).

## NON-GOALS

- No code, commits, pushes or PRs. No `-u`, no module install. `plasticos_export` stays **uninstalled**.
- Gate's own environment is out of scope. It belongs to CTO CEG, and you only hand back the public keys.
- Do not turn on the sweep (`plasticos.gate.sweep_enabled` stays `0`; both sweep crons stay inactive).
- Do not change `auto_writeback`. Run no enrichment or match except the single O3 check, after the operator says go.
- Do not put any Gate key or `GATE_URL` / `L9_*` variable on Staging.
- No `make import-*`, no `scripts/deployment/10X_Deploy_Script.sh`.

## CONSTRAINTS

- **Secrets.** A private key never appears in chat, a report, a log you paste, a commit, an `ir.config_parameter`,
  or any file inside a git checkout. Print only public keys and key ids. Report environment variables by name, never by value.
- Read before writing. Record the "before" value of every key you change.
- The Production key lives only in Production's environment. Staging's database is copied from Production, so the
  key must never be stored in the database or copied to Staging.
- Stop on the first failure and report it. No retry loops, and no workarounds that add a configuration source.
- Odoo 19 shell already runs as superuser. Use `sudo()` only on `ir.config_parameter`.

---

## P0: How does the environment reach the Odoo process on Odoo.sh? (read only, both hosts)

`gate_config.py` reads `GATE_URL` and `L9_*` from the **process environment only**. Odoo.sh documents no setting
for that. Prove the mechanism before writing anything.

On each host:

```bash
# names only, never values
for p in $(pgrep -f 'odoo-bin|odoo.service|/odoo/odoo' ); do tr '\0' '\n' < /proc/$p/environ 2>/dev/null | cut -d= -f1; done | grep -E '^(GATE_URL|L9_)' | sort -u
ls -la ~ ~/.config/odoo 2>/dev/null; grep -lE 'GATE_URL|L9_' ~/.bashrc ~/.profile ~/.config/odoo/* 2>/dev/null
grep -nE '^\s*\[|^\s*(addons_path|db_name)' ~/.config/odoo/odoo.conf 2>/dev/null | head
cat /etc/os-release | head -2; id -un
```

Also check the Odoo.sh UI, read only: Branches → <branch> → **Settings**, and project **Settings**. Look for any
"environment variables" or similar field.

Classify each host:

- **M1, already set.** The variables are in the process environment. Find where they come from, and whether that
  source survives a new build (the Odoo.sh UI, or a file outside the build container).
- **M2, persistent UI or project setting found.** Name the exact click path.
- **M3, no persistent mechanism.** Values set over SSH would vanish on the next build.

**Gate G0.** For M3, stop after P1 and report it. The CTO will route the fallback, a code change to read
`odoo.conf`, which needs an ADR. Do not edit `odoo.conf` or a shell rc file as a workaround for M3.

## P1: Key pairs (this workstation, outside every git checkout)

Production only (key id `odoo-plasticos-v1`).

```bash
mkdir -p ~/.l9/gate-keys && chmod 700 ~/.l9/gate-keys && cd ~/.l9/gate-keys && umask 077
for ENV in production; do ENV=$ENV python3 - <<'PY'
import base64, os, pathlib
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization as s
env = os.environ["ENV"]; k = Ed25519PrivateKey.generate()
priv = k.private_bytes(s.Encoding.Raw, s.PrivateFormat.Raw, s.NoEncryption())
pub = k.public_key().public_bytes(s.Encoding.Raw, s.PublicFormat.Raw)
p = pathlib.Path(f"odoo_gate_{env}.key.b64")
if p.exists(): raise SystemExit(f"{p} exists: refusing to overwrite")
p.write_text(base64.b64encode(priv).decode())
print(f"{env} public (base64):", base64.b64encode(pub).decode())
PY
done
```

Report the public key and key id `odoo-plasticos-v1`. The CTO sends them to CTO CEG, which adds them in one Gate
deploy together with the caller policy. Keep the private files until P2 is done. Delete them only when
the CTO says so, because CEG's deploy must have the matching public key first.

## P2: Odoo process environment (Production only; mechanism from P0)

**Gate G1.** Production's live code must contain Staging `0445b30`. Check with
`git -C ~/src/user merge-base --is-ancestor 0445b30 HEAD && echo OK`. If it doesn't, stop and report.
**Gate G2.** CTO CEG has confirmed that Gate is deployed with `odoo-plasticos-v1`, and `GATE_URL`, `GATE_KEY_ID` and
`GATE_PUBLIC_KEY` are filled in above. If not, stop and report.

Set exactly these seven variables through the P0 mechanism.
| Variable | Value |
|---|---|
| `GATE_URL` | `GATE_URL` (must be `https://`) |
| `L9_NODE_NAME` | `odoo` |
| `L9_SIGNING_KEY` | contents of `~/.l9/gate-keys/odoo_gate_production.key.b64`, transferred without echoing it |
| `L9_SIGNING_KEY_ID` | `odoo-plasticos-v1` |
| `L9_SIGNING_ALGORITHM` | `ed25519` |
| `L9_VERIFYING_KEYS_JSON` | `{"GATE_KEY_ID": "GATE_PUBLIC_KEY"}` |
| `L9_REQUIRE_SIGNATURE` | `true` |

Then restart the Odoo server through the Odoo.sh-supported route the mechanism requires (for example, a
**Rebuild** of that branch, which is an update and not a fresh copy of Production). Re-run the P0 names-only probe.
All seven names must be present.

## P3: Staging System Parameters (`odoo-bin shell` on the Staging host)

```python
icp = env["ir.config_parameter"].sudo()
KEYS = [
    "plasticos.gate.org_id",
    "plasticos.gate.matching_enabled",
    "plasticos.gate.enrichment_enabled",
    "plasticos.gate.timeout_seconds",
    "plasticos.gate.auto_writeback",
    "plasticos.gate.auto_writeback_operator_approved",
    "plasticos.gate.allow_insecure_http",
    "plasticos.gate.sweep_enabled",
    "plasticos.gate.converge_contract",
    "plasticos.gate.converge_cartridge_id",
    "plasticos.gate.converge_cartridge_version",
    "plasticos.gate.converge_cartridge_sha256",
]
print("BEFORE", {k: icp.get_param(k) for k in KEYS})
mods = env["ir.module.module"].search(
    [("name", "in", ["plasticos_gate", "plasticos_enrichment", "plasticos_export"])]
)
print({m.name: (m.state, m.latest_version) for m in mods})
assert dict((m.name, m.state) for m in mods).get("plasticos_export", "uninstalled") == "uninstalled"
# tenant
icp.set_param("plasticos.gate.org_id", "plasticos")
# v2 converge contract against cartridge plasticos 0.6.0
icp.set_param("plasticos.gate.converge_contract", "v2")
icp.set_param("plasticos.gate.converge_cartridge_id", "plasticos")
icp.set_param("plasticos.gate.converge_cartridge_version", "0.6.0")
icp.set_param(
    "plasticos.gate.converge_cartridge_sha256",
    "590f0fdb6ce1181b4a716f3e00512bf5425ba42d266208aa4dab18afca8dafdb",
)
# verify-only: these must already hold their seeded values; report any difference, do not change it
expect = {
    "plasticos.gate.matching_enabled": "1",
    "plasticos.gate.timeout_seconds": "30",
    "plasticos.gate.auto_writeback": "0",
    "plasticos.gate.allow_insecure_http": None,
    "plasticos.gate.sweep_enabled": "0",
}
print("DRIFT", {k: icp.get_param(k) for k, v in expect.items() if (icp.get_param(k) or None) != v})
print(
    "enrichment_enabled =", icp.get_param("plasticos.gate.enrichment_enabled")
)  # report, leave as is
crons = env["ir.cron"].with_context(active_test=False).search([("name", "ilike", "sweep")])
print("sweep crons", [(c.name, c.active) for c in crons])  # all must be False
from odoo.addons.plasticos_gate.services.gate_config import (
    resolve_converge_contract,
    resolve_tenant,
)

print("tenant", resolve_tenant(env))
print(resolve_converge_contract(env))
env.cr.commit()
print("AFTER", {k: icp.get_param(k) for k in KEYS})
```

`resolve_tenant` must print `plasticos`. The resolver must print `contract='v2'`, `0.6.0`, and the sha above.

## P4: Production System Parameters (gate G1 must hold)

Same block on the Production host (tenant `plasticos`). Before writing, the module line it prints must show
`plasticos_gate` at `19.0.1.11.0` or later. That version exists on Production only after the Staging→Production
promotion. If it is older, set only `org_id` and report. Leave the four v2 keys unset, because older code must not
be pointed at the v2 contract.

## P5: Smoke checks (runbook §4; Production only)

- **Staging check.** On Staging, the P0 names-only probe must print **nothing**: no `GATE_URL` and no `L9_*`.
- **O1 (offline).** `cfg.admission_problems()` must print `[]`. `cfg.signing_key_id` must equal `odoo-plasticos-v1`,
  and `signing_algorithm` must be `ed25519`. Print no key values.
- **O2 (one admission call, no business payload).** `ensure_admitted(...)` must return `granted_actions` containing
  `match` and `converge`. Admission for the sweep actions is not tested: the sweep stays off.
- **O3 (needs the operator's "go" at that moment).** One Enrich on one supplier facility profile, and one Match on one
  Opportunity, both on Production. With `auto_writeback=0`, the converge result must land in `review`, with no partner
  fields changed. Report run ids only, no partner names.

## DONE-CRITERIA

- P0 has a verdict (M1, M2 or M3) for each host, with evidence.
- Production's public key and key id have been handed back. No private key appeared anywhere.
- The seven environment names are present on Production (names only), and none are present on Staging.
- System Parameters are set per P3 and P4, and BEFORE, AFTER, DRIFT, enrichment_enabled and the sweep crons are reported.
- O1, O2 and O3 have results, or the gate that stopped them is named.

## ACTIVATION: report back (paste into the CTO session)

```
GATE-WIRING-RESULT
P0 staging=<M1|M2|M3 + evidence>  production=<M1|M2|M3 + evidence>
P1 key_id_production=odoo-plasticos-v1 public=<b64>
P2 production env names=<7/7 | missing ... | skipped: G1/G2 reason>  staging env names=<none (required)>
P3 staging before=<...> after=<...> drift=<...> enrichment_enabled=<...> sweep_crons=<...> tenant=<...> resolver=<...>
P4 production <same | skipped: reason>
P5 O1=<[] | problems>  O2=<granted_actions | error verbatim | waiting on CEG>  O3=<run ids + states | waiting for operator go>
plasticos_export: staging=<state> production=<state>
```
