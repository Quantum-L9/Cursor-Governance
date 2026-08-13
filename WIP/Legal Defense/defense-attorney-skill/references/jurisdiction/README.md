# Jurisdiction References

## Purpose
Jurisdiction files contain local and controlling legal authority separately from the model-agnostic defense core.

## Routing rule
Do not infer jurisdiction from accent, party names, or vague location hints. Once jurisdiction is established, load the smallest matching jurisdiction layer.

### North Carolina
Load `north_carolina/README.md` and `north_carolina/authority_hierarchy.md` before making a jurisdiction-dependent North Carolina legal conclusion.

For search/seizure issues, load `north_carolina/search_and_seizure.md` and any precedent card it requires.

For Catawba County matters, additionally load `north_carolina/catawba_county/jurisdiction_profile.md` and the local file matching the procedural issue.

## Freshness rule
Jurisdiction packs are snapshots. If legal research is available, verify controlling law and local orders before presenting a current legal conclusion. If not, disclose the pack's verified-through date and mark supersession status `UNKNOWN` where material.

## Authority discipline
- primary sources before summaries;
- holding before advocacy;
- material facts before analogy;
- controlling before persuasive;
- local procedure never overrides higher authority;
- no fabricated citations, quotations, statutes, judges, calendars, or outcomes.
