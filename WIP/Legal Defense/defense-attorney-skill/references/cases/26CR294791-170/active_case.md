# Active Case - State v. Igor Beylin

## Identity
- Case: `26CR294791-170`
- County: Catawba County, North Carolina
- Charging instrument snapshot: District Court Division, AOC-CR-116 issued 2026-04-30
- Current working event: probable-cause hearing reported for Friday, 2026-08-21, subject to live docket verification
- Arrest: 2026-04-30
- Agency: Maiden Police Department
- Primary officer: Xavier McMurtry

## Compiled case corpus
Load `compiled/index.yaml` before substantive case analysis. It is the self-contained machine-readable source layer for the selected private case materials. It contains official charging text, State Crime Laboratory findings, normalized evidence, derivative video findings, defense intelligence, arguments, source provenance, and contradictions.

The corpus is a snapshot, not a live docket. A later indictment, court order, lab report, or other verified source can supersede snapshot state through the case-state update protocol.

## Current phase
Read `phase_router.yaml`. Working snapshot: `probable_cause_2026_08_21`.

## Charging-language lock
The bundled AOC-CR-116 charging text is now directly compiled in `compiled/case_record.yaml`. Use that text for the snapshot. Do not infer that it remains the operative pleading if a later indictment or superseding instrument exists.

## Lab lock
The bundled SCL packet W202604061 is directly compiled in `compiled/lab_findings.yaml`. In that report only item 1-2 from property 3358 was chemically confirmed as MDMA at 3.07 +/- 0.03 g. Items 1-1, 2, 3, 4, and 5 received no chemical analysis in that report. Do not describe older field-test totals as lab-confirmed.

## Chronology lock
Older client/handoff chronology placing a legal-dispensary statement before the odor claim is materially contradicted by derivative bodycam analyses. Read `compiled/contradictions.yaml` and `compiled/video_findings.yaml`; do not use the older chronology as established fact.

## Record boundary
Compiled knowledge is not automatically courtroom evidence. Apply `record_boundary.yaml` before arguments, filings, or scripts.

## State entrypoints
- Read `case_state_contract.yaml` first for source ownership and update rules.
- Read `compiled/index.yaml` for immutable bundled source claims.
- Read only the dynamic/overlay files routed by `case_state_contract.yaml` for the current task.
