# North Carolina Criminal Defense Jurisdiction Layer

## Scope
Use this layer only when North Carolina law governs or the case is pending in a North Carolina court.

This pack was verified against primary North Carolina sources on **2026-08-12**. Treat that date as a freshness boundary, not a guarantee that authority remains unchanged.

## Mandatory load order
1. `authority_hierarchy.md`
2. the doctrine file matching the issue
3. any precedent card specifically implicated
4. county layer when local procedure matters

For Catawba County matters, also load `catawba_county/jurisdiction_profile.md` and the smallest relevant local file.

## Core rules
- Identify the procedural stage before applying doctrine.
- Separate federal constitutional law, North Carolina constitutional law, statutes, appellate precedent, statewide rules, and local administrative orders.
- Treat Supreme Court of North Carolina published decisions as controlling on North Carolina law unless superseded or displaced by controlling federal law.
- Treat Court of Appeals decisions according to current North Carolina rules governing precedential force; verify status before relying on a disputed proposition.
- A local administrative order governs local procedure only within its lawful scope and cannot override controlling constitutional, statutory, or appellate authority.
- Never treat a headnote or digest as a substitute for the opinion when the precise holding, factual distinction, or quoted language matters.
- If live legal research is available, verify current status before labeling an authority `CONTROLLING`.
- If live research is unavailable, label conclusions based on this pack `PACK_VERIFIED_THROUGH: 2026-08-12`.

## Primary sources
See `precedent_index.yaml` and `catawba_county/source_registry.yaml`.
