# Egress posture — decision record

**Status:** decided, awaiting one human paste
**Supersedes:** the ambiguity in `web/network-policy.md`
**Finding:** mobile bootstrap audit B-14

## The contradiction

`web/network-policy.md` lists hosts under *"Egress the agent must not need
(contract §16)"* and describes that list as "a second, independent line of
defence behind the capability architecture":

| Host | Policy says | Audited runtime |
|---|---|---|
| `app.infisical.com` | broker only — the secret backend | reachable (`200`) |
| `sonarcloud.io` | broker only — reads are brokered | reachable (`307`) |

The environment's Network access field was set to **Full** (Option A). So the
control was documented, relied upon in the threat model, and not in force.

That is worse than having no such control. An absent defence is budgeted for; a
stated one is counted on.

## Decision: tighten the field (Option B, least privilege)

Not "amend the policy to admit egress is unrestricted" — the cheaper edit, and
the wrong one. The deciding fact is that **no legitimate operation on this
surface reaches either host**:

- The agent holds no Infisical credential and has no code path that speaks to
  `app.infisical.com`. The broker does, from the trusted side.
- Authenticated Sonar reads resolve through the `sonar.read_issues` capability,
  which the broker executes. Unauthenticated public reads are a convenience the
  publish path does not depend on.

Blocking both costs this surface nothing measurable and converts a documented
control into a real one. When the cost of enforcement is zero, "we wrote it down
but did not do it" has no defence.

## What this requires

One paste, by a human, into claude.ai/code → environment → **Network access**:
switch from **Full** to **Custom**, using the host list in
`web/network-policy.md` § "Option B". An agent cannot write this field.

Until then the probe reports the gap rather than failing, so it stays useful on
both sides of the change:

```bash
python3 ops/scripts/probe_network_posture.py            # report
python3 ops/scripts/probe_network_posture.py --assert   # enforce, once pasted
```

## What this does not claim

Least privilege is defence in depth, not the primary control. The primary
control is that this surface holds no credential at all — verified separately,
and unaffected by whichever way the Network access field is set.
