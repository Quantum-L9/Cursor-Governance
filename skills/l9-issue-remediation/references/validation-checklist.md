<!-- L9_META
l9_schema: 1
parent: l9-issue-remediation
layer: reference
role: validation_checklist
tags: [issues, validation, done-when]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-29
/L9_META -->

# Validation Checklist

## Pack structure

- [ ] `SKILL.md` frontmatter: name, description, audit fields under `metadata:`, `disable-model-invocation: true`
- [ ] `agents/meta.yaml` present; no `agents/openai.yaml`
- [ ] Every `references/` file linked from `SKILL.md`
- [ ] Every `scripts/` file named in SKILL.md or linked refs
- [ ] Zero stub / TBD / unfinished sections

## Diagnose (auditor)

- [ ] `fleet_discover.py` returns non-archived Quantum-L9 repos
- [ ] `issue_ingest.py` produces secret-free JSON
- [ ] Verdict emitted only after ingest + live `gh issue view` verify
- [ ] Already-resolved / phantom close allowed with evidence
- [ ] No commit / push / fix
- [ ] Never chains `/l9-pr-remediation`

## Converge (remediator)

- [ ] `max_clusters_per_invoke: all` — leverage-ranked queue, not sticky ≤ 1
- [ ] `verify_before_trust: true` — recreate live issue; close if phantom; remediate only if `exists`
- [ ] Do not stop between automatable issues; HUMAN/ARCHITECTURE uses recommended-A MCQ then resume
- [ ] Ownership classified before edit
- [ ] CROSS_REPO fixed at obvious owner
- [ ] Cycles ≤ 3 per cluster; land on matching open PR or stacked newest
- [ ] No workflow/CI infra edits; no merge; no force-push
- [ ] `open_issues == 0` before any `/l9-pr-remediation` invoke
- [ ] `status=fixed` issues are CLOSED (not comment-only)
- [ ] PICKUP required; issue comments on all cluster issues
- [ ] `TODO.md` updated only when pre-existing

## Wiring

- [ ] `l9-wire-skill-into-repo` PASS
- [ ] `AUTONOMY_MANIFEST.yaml` `explicit_only` row present
- [ ] `/issues` remediator Converge-by-default; `/issues diagnose` auditor
- [ ] `/l9-issue-remediation` slash exists and matches Converge
- [ ] `scripts/self_test.py` PASS
