---
name: Resolve Documents and Logistics BRS drift
overview: 'Relocate the Linda-owned Native-First BRS material so each rule set sits
  with its concern: install the BRS-POS-10 chapter verbatim into plasticos_logistics/business_rules
  with recorded provenance, transfer ownership of BRS-POS-09-R006..R012 to plasticos_logistics
  by dated supersession entries in both packs without rewriting any frozen chapter
  bytes, then wire both packs into their modules via R...'
todos:
- id: T01
  content: 'Resolve the stash by subject, not by index alone. Require stash@{8} subject
    ''remaining untracked before leaving only Staging (2026-11-01)''; if the subject
    differs, search stashes for that subject and stop if it is absent. Extract RULES/BRS-POS-10-linda-logistics-commercial-and-physical-communication.md,
    SHA256SUMS, and the covering REGISTRY/rules.json rows via git show ''<stash>^3:docs/campaigns/10-26-26/PlasticOS_Native_First_BRS_v1.0.0_2026-10-25/...''
    to /tmp/brs-pos-10-extract/. Verify the chapter sha256 against SHA256SUMS. Never
    pop or apply the stash. Mismatch or missing blob: blocked, stop. Fallback only:
    /Users/ib-mac/Dropbox/Downloads (DBOX)/PlasticOS_Native_First_BRS_v1.0.0_2026-10-25/
    verified against its SHA256SUMS. Read tests/contracts/test_logistics_brs_registry.py
    fully before T02.'
  status: completed
- id: T02
  content: 'Install the chapter byte-for-byte as plasticos_logistics/business_rules/BRS-POS-10-linda-logistics-commercial-and-physical-communication.md.
    Create NATIVE_FIRST_REGISTRY.json beside it: source pack name and version, chapter
    sha256 from SHA256SUMS, the 16 rule IDs with titles and scope classes from plasticos_documents/business_rules/ALL_170_RULES_SCOPE.csv
    rows 129-144, install date, and a statement that this installs one chapter without
    admitting the other eleven Native-First chapters. Do not touch plasticos_logistics/business_rules/REGISTRY.json.
    Documents REGISTRY.json is T03 only, and only for the ownership_transferred list.'
  status: completed
- id: T03
  content: 'Transfer external-send ownership of BRS-POS-09-R006..R012 by dated supersession,
    without treating installed text as deleted. Exact titles from ALL_170_RULES_SCOPE.csv:
    R006 Only one external reminder writer; R007 Supplier document business clock;
    R008 Carrier document business clock; R009 Buyer document business clock; R010
    No duplicate daily touch; R011 Quiet hours and locale aware deadlines; R012 Stop
    on verified or inapplicable. Documents: dated SUPERSESSION.md entry; set EFFECTIVE_RULES.md/.json
    semantic_owner of those seven to plasticos_logistics (external send) while Documents
    keeps status/activity supply; reclassify the seven CSV rows from DOCUMENTS_BRS_LOCAL
    to CROSS_DOMAIN_CONSUMER_REFERENCE. Do not change REGISTRY.json source_rule_ids
    or local_rule_count (both stay 44) or external_rule_count (stays 126): 44+126=170
    counts installed verbatim text, not current owner. Add ownership_transferred listing
    the seven IDs and the logistics owner. Rewrite README.md and OWNERSHIP_AND_INTEROP.md
    so they stop saying all 44 are Documents-owned: 44 installed verbatim, 37 remain
    Documents-owned, seven external-send owners moved. CROSS_DOMAIN_ACCEPTANCE.json:
    one owner note that AC-DOC-X10, X11, X12 (and any other case citing these IDs)
    still test the rule text but the external sender is logistics; do not change positive_expected
    or result (they stay NOT_RUN). Chapter bytes unchanged. Logistics SUPERSESSION.md:
    matching dated admission, cross-referenced to BRS-02-R007, BRS-06-R039, BRS-07-R051.
    Grep tests/ and ci/ for a literal assertion of 44 Documents-owned rules before
    committing.'
  status: completed
- id: T04
  content: 'Wire agent bindings outside the preserved overlay markers. Do not edit
    bytes between LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN and _END in plasticos_logistics/AGENTS.md
    or business_rules/README.md. Those blocks say BRS-POS-* is reference-only and
    not a second copied authority. After each _END marker, add one paragraph: the
    dated supersession admits exactly one copied chapter, BRS-POS-10, and admits BRS-POS-09-R006..R012
    as Linda external-send obligations; every other BRS-POS chapter stays a cross-domain
    reference. Add the same two items to the read-first list that already sits above
    the marker in AGENTS.md. Documents README.md and plasticos_documents/AGENTS.md:
    one sentence plus pointer that external-send ownership of the seven IDs moved,
    and that 44 still means installed text. Both packs keep the statement that BRS-POS-04..08
    and 11..12 stay with their owners.'
  status: completed
- id: T05
  content: 'Contract tests. tests/contracts/test_native_first_brs_registry.py: installed
    chapter sha256 equals NATIVE_FIRST_REGISTRY.json and the source SHA256SUMS line;
    16 headings match registry IDs. tests/contracts/test_documents_brs_registry.py:
    ALL_170_RULES_SCOPE.csv has exactly 37 DOCUMENTS_BRS_LOCAL rows; the seven IDs
    are CROSS_DOMAIN_CONSUMER_REFERENCE; EFFECTIVE_RULES.json semantic_owner for those
    seven is plasticos_logistics; REGISTRY.json source_rule_ids length and local_rule_count
    stay 44 and external_rule_count stays 126; ownership_transferred lists the seven;
    the three chapter files are byte-unchanged against recorded hashes; logistics
    and documents AGENTS.md/README.md contain the post-marker exception paragraph
    and do not differ inside the 2026-10-26 marker blocks from HEAD. Do not modify
    the original assertions in test_logistics_brs_registry.py.'
  status: completed
- id: T06
  content: 'Gate and publish. ruff check --fix and ruff format on the new test files;
    run the three contract test files with pytest; then scoped commit of exactly this
    plan''s file list and make pr into Staging (stack on the open PR chain tip when
    one exists). Docs-plus-pure-tests scope: pr_check_scope skips Docker smoke.'
  status: completed
isProject: false
built: true
status: built
---

# PLAN: Resolve Documents and Logistics BRS drift

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `resolve_documents_and_logistics_brs_drift_43ce1197.plan.md`
> **Law:** executable only when baseline matches, capability probes pass, invariants match, and envelope is respected. Markdown completeness alone is insufficient.

## Execute via Cursor Build

Press **Build**. Plan on the current workspace. Execute on the unique open-PR chain tip.

- If any open PR exists: **never** branch from `origin/main`. Start from the unique chain tip (`PR_STACK=auto`). Use `agent_worktree_start.sh` when this checkout is not already that tip. Sibling open-PR chains fail closed.
- If the board is empty: `origin/main` is allowed.
- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a **planning** requirement.
- After Build todos complete: scoped-commit (pathspecs), `l4_local.py authorize-release`, then `PR_STACK=auto PR_REMEDIATE=0 make pr`. Do not skip `make pr`.
- The finish reply **must** display the opened PR URL as proof. Without that URL the Build is incomplete.

## Recursive Alignment record

Auditor: `.cursor-commands/kernels/Recursive Alignment.md` (`recursive_architecture_alignment_auditor` 1.0). Target is this plan. The user authorized this in-place revision. The BRS trees are not modified by the audit. Corrections below are in the plan text; none are claimed executed.

```yaml
audit_status: PartiallySucceeded
readiness_status: Unknown
convergence_status: Partial
target_binding:
  roots:
    - "/Users/ib-mac/.cursor/plans/brs_drift_resolution_45077922.plan.md"
    - "/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19/.l9/plans/brs_drift_resolution.plan.json"
  artifact_type: implementation_plan
  identifier: plan.simple.resolve_documents_and_logistics_brs_drift.v1
  revision: "rendered 2026-11-05 from validated PLAN_DOCUMENT; kernel revision applied in place"
  coupled_evidence_read:
    - plasticos_documents/business_rules/REGISTRY.json
    - plasticos_documents/business_rules/ALL_170_RULES_SCOPE.csv
    - plasticos_documents/business_rules/EFFECTIVE_RULES.json
    - plasticos_documents/business_rules/OWNERSHIP_AND_INTEROP.md
    - plasticos_documents/business_rules/CROSS_DOMAIN_ACCEPTANCE.json
    - plasticos_logistics/AGENTS.md
    - plasticos_logistics/business_rules/README.md
    - tests/contracts/test_logistics_brs_registry.py
authorized_scope: "This plan's contract: ownership split, write set, proofs, and source binding."
excluded_scope:
  - "INVARIANTS.md and .cursor/rules (separate plan)"
  - "Addon Python, XML, and manifests"
  - "Chapter bytes of BRS-01..07 and BRS-POS-02/03/09"
  - "Execution of T01-T06"
source_authority_used:
  - source: ".cursor-commands/kernels/Recursive Alignment.md"
    precedence: 1
    scope: "audit output contract"
  - source: "both packs' SUPERSESSION law and the 2026-10-26 overlay markers"
    precedence: 2
    scope: "how ownership may change"
  - source: "plasticos_documents/business_rules/REGISTRY.json local_rule_count 44, external_rule_count 126"
    precedence: 3
    scope: "installed-text arithmetic 44+126=170"
  unresolved_conflicts: []
architecture_adapters:
  - id: plasticos_brs_preservation
    name: "Module-local BRS preservation and supersession"
    version: "logistics overlay 2026-10-26; documents registry 1.0.0-documents-repository-install"
    governing_source: "plasticos_logistics/AGENTS.md, plasticos_logistics/business_rules/README.md, plasticos_documents/business_rules/REGISTRY.json"
    status: Applied
    mandatory_rules:
      - "Frozen chapter bytes change only by a new verbatim install or not at all"
      - "Later ownership changes are dated supersession entries"
      - "Bytes inside LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN/END stay unchanged"
    prohibited_patterns:
      - "A second copied Native-First authority inside logistics except the one chapter this plan admits"
      - "Rewriting BRS-01..07 or the three Documents chapters"
normalized_context:
  purpose: "Put BRS-POS-10 and the external-send owner of BRS-POS-09-R006..R012 with logistics, and keep every other concern where it already sits."
  consumers: "logistics and documents coding agents via AGENTS.md read-first lists; contract tests under tests/contracts/"
artifact_inventory:
  in_plan_write_allow: "logistics BRS-POS-10 chapter, NATIVE_FIRST_REGISTRY.json, both SUPERSESSION.md, Documents EFFECTIVE_RULES, scope CSV, README, OWNERSHIP_AND_INTEROP, REGISTRY.json ownership list, CROSS_DOMAIN_ACCEPTANCE owner note, both AGENTS.md, two new contract tests"
  inspected_not_modified: "the coupled_evidence_read paths"
boundary_map:
  component_responsibilities:
    documents: "Installed verbatim text of BRS-POS-02, 03, 09 (44 IDs). Status and activity supply for the seven transferred clauses."
    logistics: "BRS-01..07 (60 IDs) plus, after Build, copied BRS-POS-10 and external-send ownership of BRS-POS-09-R006..R012."
  communication_paths: "Dated SUPERSESSION.md entries in both packs. No chapter split. No edit inside the 2026-10-26 markers."
  routing_ownership: "AGENTS.md read-first lists. The exception paragraph sits after each _END marker."
  data_ownership: "REGISTRY.json source_rule_ids stay the text inventory. ownership_transferred is the owner overlay. Scope CSV class is the Documents-owned count."
  security_boundary: "No live mail, cron, secrets, or runtime activation."
  validation_ownership: "V1 native-first hash, V2 untouched logistics registry test, V3 documents registry plus marker-paragraph assertions, V4 ruff, V5 make pr, V6 pre-commit catalog."
alignment_summary: "The plan's earlier draft would have installed a copied BRS-POS chapter into a module whose preserved overlay forbids that, and would have dropped the Documents owned-count to 37 while REGISTRY.json stayed 44+126=170. This revision keeps the install, records the exception after the markers, and splits installed-text count from owner."
alignment_score:
  weighted_overall: "90/100"
  warning: "Score does not override Unknown readiness. V1-V6 are not_run and U1 is open."
  domains:
    - domain: intent_and_scope
      weight: 10
      score: 10
      status: Passed
    - domain: communication_contracts
      weight: 10
      score: 10
      status: Passed
    - domain: routing_and_integration
      weight: 10
      score: 10
      status: Passed
    - domain: ownership_and_authority
      weight: 15
      score: 15
      status: Passed
    - domain: structure_and_source_of_truth
      weight: 10
      score: 10
      status: Passed
    - domain: schema_and_configuration
      weight: 10
      score: 10
      status: Passed
    - domain: security
      weight: 15
      score: 15
      status: Passed
    - domain: reliability_and_observability
      weight: 10
      score: 10
      status: Passed
    - domain: testing_and_validation
      weight: 10
      score: 0
      status: Unknown
  excluded_domains: []
  unknown_domains: [testing_and_validation]
critical_violations: []
high_violations:
  - id: RA-H1
    severity: High
    confidence: Confirmed
    status: Resolved
    release_blocking: false
    governing_rule: "No conflicting source of truth; 44+126=170 counts installed text"
    rule_source: "plasticos_documents/business_rules/REGISTRY.json; kernel source_of_truth_aligned"
    affected: "T03 and Documents README / OWNERSHIP_AND_INTEROP.md"
    evidence: "REGISTRY.json local_rule_count 44 and external_rule_count 126. README.md lines 9 and 13 and OWNERSHIP_AND_INTEROP.md line 3 call all 44 Documents-owned. The prior plan set the README count to 37 and left REGISTRY.json out of write_allow."
    observed: "Prior plan text changed the owned-count and left the registry at 44."
    expected: "source_rule_ids, local_rule_count, and external_rule_count stay 44/44/126. ownership_transferred lists the seven IDs. Scope CSV Documents-owned rows become 37. README and OWNERSHIP say both facts."
    impact: "A Build of the prior text would have shipped two counts for the same 44 IDs."
    root_cause: "Installed-text count and current owner were treated as one number."
    smallest_correction: "T03 as now written. REGISTRY.json, OWNERSHIP_AND_INTEROP.md, and CROSS_DOMAIN_ACCEPTANCE.json are in write_allow."
    owner: "plasticos_documents/business_rules"
    dependencies: []
    closing_validation: "V3"
  - id: RA-H2
    severity: High
    confidence: Confirmed
    status: Resolved
    release_blocking: false
    governing_rule: "Do not edit the preserved overlay; a later supersession names the only admitted exception"
    rule_source: "plasticos_logistics/AGENTS.md lines 9-15; business_rules/README.md lines 34-42"
    affected: "T02 install and T04 routing"
    evidence: "Inside the markers, both files say BRS-POS-* is reference-only and not a second copied authority inside the module."
    observed: "Prior T04 added BRS-POS-10 to the read-first list and did not bound that sentence."
    expected: "Marker bytes unchanged. After each _END marker, one paragraph admits only BRS-POS-10 as a copied chapter and only R006..R012 as Linda external-send obligations."
    impact: "The install would have contradicted the module contract it claims to preserve."
    root_cause: "The plan treated the overlay as commentary rather than a frozen contract."
    smallest_correction: "T04 as now written, plus the logistics SUPERSESSION.md admission in T03."
    owner: "plasticos_logistics"
    dependencies: [RA-H1]
    closing_validation: "V3 marker-byte assertion"
medium_violations:
  - id: RA-M1
    severity: Medium
    confidence: Confirmed
    status: Resolved
    release_blocking: false
    governing_rule: "Validation must cover the claim it is cited for"
    rule_source: "kernel testing_and_validation"
    affected: "SP-04 proof"
    evidence: "Prior SP-04 cited V3, whose pass text did not read AGENTS.md or README.md."
    observed: "Agent-routing success was proved by a registry-count test."
    expected: "V3 asserts the post-marker paragraphs and unchanged marker bytes."
    impact: "A green V3 could have shipped with the overlay contradiction still in place."
    root_cause: "One test id was reused for two unrelated claims."
    smallest_correction: "T05 and V3 pass_criteria now include those assertions."
    owner: "tests/contracts"
    dependencies: [RA-H2]
    closing_validation: "V3"
low_violations:
  - id: RA-L1
    severity: Low
    confidence: Confirmed
    status: Resolved
    release_blocking: false
    governing_rule: "Bind the exact source revision, not an unstable index"
    rule_source: "kernel target_contract"
    affected: "T01 source"
    evidence: "stash@{8} was the only identifier. Its subject is 'remaining untracked before leaving only Staging (2026-11-01)'."
    observed: "A later stash push would make @{8} a different tree."
    expected: "T01 matches that subject before reading blobs."
    impact: "Wrong chapter bytes, caught only if SHA256SUMS also moved."
    root_cause: "Stash indexes are not identities."
    smallest_correction: "T01 subject check, as now written."
    owner: "T01"
    dependencies: []
    closing_validation: "C1"
  - id: RA-L2
    severity: Low
    confidence: Confirmed
    status: Open
    release_blocking: false
    governing_rule: "Compensation must be able to undo the side effect"
    rule_source: "kernel reliability; renderer side-effect row for T01"
    affected: "T01 compensation cell"
    evidence: "The projected row says git restore -- /tmp/brs-pos-10-extract/. git restore does not delete an untracked temp directory."
    observed: "Renderer default compensation."
    expected: "rm -rf /tmp/brs-pos-10-extract"
    impact: "A leftover temp dir. No repo file is at risk."
    root_cause: "The projection assigns git restore to every filesystem todo."
    smallest_correction: "Executor removes the temp dir. Do not treat that cell as the compensation."
    owner: "projection renderer"
    dependencies: []
    closing_validation: "none required before make pr"
unknowns:
  - id: U1
    why: "P1 listed the chapter path in stash@{8}. It did not hash the blob."
    affected_conclusion: "readiness_status and C1"
    minimum_evidence: "sha256 of the extracted chapter equals its SHA256SUMS line"
intent_and_scope_compliance:
  status: Passed
  governing_rules: ["scope.out keeps BRS-POS-04..08 and 11..12 with their owners", "no runtime activation"]
  evidence: "scope.out and T04 last sentence"
  open_violations: []
  closing_validation: "V5 file list"
communication_contract_compliance:
  status: Passed
  governing_rules: ["supersession is the only way to change ownership", "marker bytes are frozen"]
  evidence: "T03 and T04"
  open_violations: []
  closing_validation: "V3"
routing_and_integration_compliance:
  status: Passed
  governing_rules: ["RA-H2"]
  evidence: "T04 post-marker paragraph"
  open_violations: []
  closing_validation: "V3"
authority_boundary_compliance:
  status: Passed
  governing_rules: ["RA-H1", "one external sender"]
  evidence: "EFFECTIVE_RULES.json semantic_owner of R006 is currently the shared triple 'Odoo Documents/Activity, PlasticOS obligation service, Linda external mail'. CSV rows 117-123 are DOCUMENTS_BRS_LOCAL. AC-DOC-X10 already says no Documents external reminder if Linda is authoritative."
  open_violations: []
  closing_validation: "V3"
structure_and_source_of_truth_compliance:
  status: Passed
  governing_rules: ["BRS files live in the module business_rules directory, not docs/"]
  evidence: "plasticos_logistics/AGENTS.md line 5; T02 path"
  open_violations: []
  closing_validation: "C2"
schema_and_configuration_compliance:
  status: Passed
  governing_rules: ["RA-H1 arithmetic"]
  evidence: "REGISTRY.json fields source_rule_ids, local_rule_count, external_rule_count"
  open_violations: []
  closing_validation: "V3"
security_compliance:
  status: Passed
  governing_rules: ["no secrets", "no live send"]
  evidence: "execution_envelope.secrets.access none; scope.out live mail and cron"
  open_violations: []
  closing_validation: "V6"
reliability_observability_compliance:
  status: Passed
  governing_rules: ["C1 blocks install on hash mismatch"]
  evidence: "checkpoints C1-C3"
  open_violations: [RA-L2]
  closing_validation: "C1"
testing_validation_compliance:
  status: Unknown
  governing_rules: ["do not claim Ready while validation is not run"]
  evidence: "E-V1..E-V6 status not_run"
  open_violations: []
  closing_validation: "V1 V2 V3 V4 V5 V6"
overbuilt_vs_underbuilt:
  overbuilt: []
  underbuilt:
    - "Prior plan omitted REGISTRY.json, OWNERSHIP_AND_INTEROP.md, and CROSS_DOMAIN_ACCEPTANCE.json. Now in the write set."
  speculative: []
  simplest_high_value_correction: "Keep 44+126 as the text inventory and record the seven owners separately."
leverage_analysis:
  ranked: [T02, T01, T03, T04, T05, T06]
  shared_cause: "The Native-First pack was never committed, so Documents registered every chapter it held as local, including Linda's send rules."
correction_roadmap:
  - id: CR-1
    finding: U1
    order: 1
    owner: T01
    prerequisites: "stash subject match"
    artifacts: ["/tmp/brs-pos-10-extract/"]
    risk: "medium"
    value: "Unblocks every later todo"
    closing_validation: C1
    implemented: false
  - id: CR-2
    finding: RA-H1
    order: 2
    owner: T03
    prerequisites: [CR-1]
    artifacts: ["Documents REGISTRY.json", "OWNERSHIP_AND_INTEROP.md", "scope CSV", "EFFECTIVE_RULES", "CROSS_DOMAIN_ACCEPTANCE.json", "both SUPERSESSION.md"]
    risk: "medium"
    value: "One owner per clause without a second count"
    closing_validation: V3
    implemented: false
  - id: CR-3
    finding: RA-H2
    order: 3
    owner: T04
    prerequisites: [CR-2]
    artifacts: ["plasticos_logistics/AGENTS.md", "plasticos_logistics/business_rules/README.md", "plasticos_documents/AGENTS.md"]
    risk: "low"
    value: "The install no longer contradicts the overlay"
    closing_validation: V3
    implemented: false
minimum_safe_next_action:
  action: "Press Build and run T01 only through the sha256 compare. Stop if the stash subject or the hash does not match."
  rationale: "U1 is the only open item that can invalidate every later byte."
  resolves: U1
  expected_evidence: "C1 hash equality"
validation_gates:
  target_bound: Passed
  authority_resolved: Passed
  inventory_complete: Passed
  boundary_map_complete: Passed
  architecture_adapters_correctly_applied: Passed
  findings_evidence_backed: Passed
  severity_consistent: Passed
  contracts_aligned: Passed
  routing_and_authority_aligned: Passed
  source_of_truth_aligned: Passed
  schema_and_configuration_aligned: Passed
  security_aligned: Passed
  reliability_and_observability_aligned: Passed
  testing_and_validation_aligned: Unknown
  correction_roadmap_actionable: Passed
  convergence_verified: Unknown
  overall_audit: Unknown
residual_risks:
  - "RA-L2 temp-dir compensation cell is wrong and non-blocking."
  - "CROSS_DOMAIN_ACCEPTANCE results stay NOT_RUN. This plan does not run them."
  - "Working tree on fix/documents-loop-query-batch is dirty. Scoped commit must not take those model edits."
convergence:
  completed_passes: [context_and_scope_lock, contract_and_ownership, convergence]
  skipped_passes:
    - pass: runtime_behavior
      reason: "Docs and tests only. No Odoo process was run."
  material_work_remaining: "U1 hash probe, then Build of T02-T06. Findings RA-H1, RA-H2, RA-M1, RA-L1 are resolved in the plan text and not in the trees."
  evidence: "REGISTRY.json, AGENTS.md marker block, scope CSV rows 117-123, EFFECTIVE_RULES.json R006-R012, AC-DOC-X10..X12."
```

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.simple.resolve_documents_and_logistics_brs_drift.v1` |
| name | Resolve Documents and Logistics BRS drift |
| overview | Relocate the Linda-owned Native-First BRS material so each rule set sits with its concern: install the BRS-POS-10 chapter verbatim into plasticos_logistics/business_rules with recorded provenance, transfer ownership of BRS-POS-09-R006..R012 to plasticos_logistics by dated supersession entries in both packs without rewriting any frozen chapter bytes, then wire both packs into their modules via README/AGENTS read-first lists, registries, and hash-locked contract tests. Alignment auditor: .cursor-commands/kernels/Recursive Alignment.md (recursive_architecture_alignment_auditor 1.0), audit-only except this authorized in-place plan revision. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial`; remaining unknowns: U1 |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-05T16:04:27+00:00 |
| updated_at | 2026-11-05T16:04:27+00:00 |
| depth | `standard` |
| estimate | half day |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | validated PLAN_DOCUMENT JSON (`validate_plan_document.py`) |
| plan_class | `bounded_execution_contract` — PLAN_DOCUMENT mode `plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Execute via Cursor Build; stacked make pr if any open PR exists; no redesign unless plan_class requires it |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-11-05T16:04:27+00:00` |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| branch | `test/retire-stale-proofs` |
| commit_sha | `077ffad4a2825db41b5fcea65a013812129b05ab` |
| dirty | `false` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

Relocate the Linda-owned Native-First BRS material so each rule set sits with its concern: install the BRS-POS-10 chapter verbatim into plasticos_logistics/business_rules with recorded provenance, transfer ownership of BRS-POS-09-R006..R012 to plasticos_logistics by dated supersession entries in both packs without rewriting any frozen chapter bytes, then wire both packs into their modules via README/AGENTS read-first lists, registries, and hash-locked contract tests. Alignment auditor: .cursor-commands/kernels/Recursive Alignment.md (recursive_architecture_alignment_auditor 1.0), audit-only except this authorized in-place plan revision.

### Scope in

- plasticos_logistics/business_rules/ (new BRS-POS-10 chapter file, NATIVE_FIRST_REGISTRY.json, README.md additive section, SUPERSESSION.md dated entry)
- plasticos_documents/business_rules/ (SUPERSESSION.md dated entry; EFFECTIVE_RULES.md/.json semantic_owner for the seven IDs; ALL_170_RULES_SCOPE.csv seven rows; README.md and OWNERSHIP_AND_INTEROP.md ownership wording; REGISTRY.json ownership_transferred list while source_rule_ids and local_rule_count stay 44; CROSS_DOMAIN_ACCEPTANCE.json owner note on AC-DOC-X10..X12 only)
- plasticos_logistics/AGENTS.md and plasticos_documents/AGENTS.md read-first pointers
- tests/contracts/test_native_first_brs_registry.py (new), tests/contracts/test_documents_brs_registry.py (new), tests/contracts/test_logistics_brs_registry.py (extend only, original assertions untouched)

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | BRS-POS-10 chapter installed byte-identical to the source pack with sha256 provenance recorded in NATIVE_FIRST_REGISTRY.json and proven by V1 | `quality_gate` | V1: `python3 -m pytest tests/contracts/test_native_first_brs_registry.py -q` → pass; includes assertion that installed chapter sha256 equals the source SHA256SUMS value recorded in NATIVE_FIRST_REGISTRY.json | `true` |
| SP-02 | Seven BRS-POS-09 clauses (R006..R012) owned by plasticos_logistics via dated supersession in both packs with Documents chapter bytes unchanged, proven by V3 | `quality_gate` | V3: `python3 -m pytest tests/contracts/test_documents_brs_registry.py -q` → pass; 37 DOCUMENTS_BRS_LOCAL rows; seven IDs cross-domain; semantic_owner plasticos_logistics; REGISTRY source_rule_ids and local_rule_count remain 44; external_rule_count remains 126; chapter bytes unchanged; post-marker exception paragraph present in logistics and documents AGENTS.md and README.md; bytes inside the 2026-10-26 markers unchanged versus HEAD | `true` |
| SP-03 | Existing logistics preservation gate unbroken: original BRS-01..07 assertions in test_logistics_brs_registry.py pass unmodified, proven by V2 | `quality_gate` | V2: `python3 -m pytest tests/contracts/test_logistics_brs_registry.py -q` → pass with the original BRS-01..07 assertions unmodified | `true` |
| SP-04 | Agent routing wired without contradicting the preserved 2026-10-26 overlays: an additive paragraph after each LINDA_BRS_NATIVE_ALIGNMENT_20261026_END marker names BRS-POS-10 and BRS-POS-09-R006..R012 as the only admitted exception, proven by V3 assertions that read those paragraphs | `quality_gate` | V3: `python3 -m pytest tests/contracts/test_documents_brs_registry.py -q` → pass; 37 DOCUMENTS_BRS_LOCAL rows; seven IDs cross-domain; semantic_owner plasticos_logistics; REGISTRY source_rule_ids and local_rule_count remain 44; external_rule_count remains 126; chapter bytes unchanged; post-marker exception paragraph present in logistics and documents AGENTS.md and README.md; bytes inside the 2026-10-26 markers unchanged versus HEAD | `true` |
| SP-05 | Lint and repo gates green on the new test files, proven by V4 and V5 | `quality_gate` | V4: `ruff check tests/contracts && ruff format --check tests/contracts` → clean; V5: `make pr` → local gate green (pre-commit catalog .pre-commit-config.yaml), PR opened into Staging, PR URL displayed | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.resolve_documents_and_logistics_brs_drift.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.resolve_documents_and_logistics_brs_drift.v1` |
| source_ref | `plan.simple.resolve_documents_and_logistics_brs_drift.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.resolve_documents_and_logistics_brs_drift.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `Bind workspace: git rev-parse --abbrev-ref HEAD; git status --porcelain \| head. Current checkout is fix/documents-loop-query-batch and dirty with unrelated logistics/documents model edits that must stay untouched; the Build branch starts from the open PR chain tip or Staging (capitalized).` | Branch and dirty state recorded; no touched path overlaps this plan's file set | `true` |
| P1 | pre-validation (status `passed`) | `Verify source presence only: git stash show --include-untracked --name-only 'stash@{8}' lists RULES/BRS-POS-10-linda-logistics-commercial-and-physical-communication.md and SHA256SUMS under docs/campaigns/10-26-26/PlasticOS_Native_First_BRS_v1.0.0_2026-10-25/. This probe did not compute the chapter sha256. Stash index is unstable; T01 must match the subject 'remaining untracked before leaving only Staging (2026-11-01)' before reading blobs.` | Both paths listed in stash@{8}. Hash equality is U1, not this probe. | `true` |
| P2 | pre-validation (status `passed`) | `Verify preservation gates: tests/contracts/test_logistics_brs_registry.py asserts REGISTRY.json brs_files == [BRS-01.md..BRS-07.md] and per-file sha256; plasticos_documents/business_rules chapters are byte-frozen per that pack's SUPERSESSION law` | Constraints read and bound into scope.out | `true` |
| P3 | pre-validation (status `passed`) | `Hook catalog: .pre-commit-config.yaml (39 hooks; gitleaks, ruff, odoo scanners) governs the commit; make pr runs the full local gate` | Catalog named; docs-plus-pure-tests scope means pr_check_scope skips Docker smoke | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `plasticos_logistics/business_rules/BRS-POS-10-linda-logistics-commercial-and-physical-communication.md`, `plasticos_logistics/business_rules/NATIVE_FIRST_REGISTRY.json`, `plasticos_logistics/business_rules/README.md`, `plasticos_logistics/business_rules/SUPERSESSION.md`, `plasticos_logistics/AGENTS.md`, `plasticos_documents/business_rules/SUPERSESSION.md`, `plasticos_documents/business_rules/EFFECTIVE_RULES.md`, `plasticos_documents/business_rules/EFFECTIVE_RULES.json`, `plasticos_documents/business_rules/ALL_170_RULES_SCOPE.csv`, `plasticos_documents/business_rules/README.md`, `plasticos_documents/AGENTS.md`, `tests/contracts/test_native_first_brs_registry.py`, `tests/contracts/test_documents_brs_registry.py`, `tests/contracts/test_logistics_brs_registry.py`, `plasticos_documents/business_rules/OWNERSHIP_AND_INTEROP.md`, `plasticos_documents/business_rules/REGISTRY.json`, `plasticos_documents/business_rules/CROSS_DOMAIN_ACCEPTANCE.json`
- **write_deny:** `plasticos_logistics/business_rules/BRS-01.md`, `plasticos_logistics/business_rules/BRS-02.md`, `plasticos_logistics/business_rules/BRS-03.md`, `plasticos_logistics/business_rules/BRS-04.md`, `plasticos_logistics/business_rules/BRS-05.md`, `plasticos_logistics/business_rules/BRS-06.md`, `plasticos_logistics/business_rules/BRS-07.md`, `plasticos_logistics/business_rules/REGISTRY.json`, `plasticos_documents/business_rules/BRS-POS-02-native-documents-originals-and-intake.md`, `plasticos_documents/business_rules/BRS-POS-03-evidence-classification-attribution-and-verification.md`, `plasticos_documents/business_rules/BRS-POS-09-native-documents-requests-activities-automation-and-scheduler.md`, `plasticos_logistics/models/`, `plasticos_documents/models/`, `INVARIANTS.md`, `.cursor/rules/`, `Bytes between LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN and LINDA_BRS_NATIVE_ALIGNMENT_20261026_END`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `python3 -m pytest tests/contracts/test_native_first_brs_registry.py tests/contracts/test_logistics_brs_registry.py tests/contracts/test_documents_brs_registry.py -q`, `ruff check tests/contracts && ruff format --check tests/contracts`, `.pre-commit-config.yaml`, `make pr`, `python3 -m pytest tests/contracts/test_native_first_brs_registry.py -q`, `python3 -m pytest tests/contracts/test_logistics_brs_registry.py -q`, `python3 -m pytest tests/contracts/test_documents_brs_registry.py -q`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | `named_services_only` |
| allowed_services | `github.com (make pr publication only)` |

### Secrets

| Field | Value |
|-------|-------|
| access | `none` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- Byte-for-byte preservation of all frozen BRS chapter files; changes only via dated SUPERSESSION entries with stable rule IDs
- REGISTRY.json brs_files stays exactly [BRS-01.md..BRS-07.md] with original hashes
- make pr is the only publication path; target branch Staging
- Docs-and-tests only: no module version bump, no make update, no runtime activation
- Bytes inside LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN/END in plasticos_logistics/AGENTS.md and business_rules/README.md stay unchanged; the BRS-POS-10 exception is an additive paragraph after _END plus a SUPERSESSION.md entry

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T01 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- /tmp/brs-pos-10-extract/` | `false` |
| T02 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_logistics/business_rules/BRS-POS-10-linda-logistics-commercial-and-physical-communication.md plasticos_logistics/business_rules/NATIVE_FIRST_REGISTRY.json` | `false` |
| T03 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_documents/business_rules/SUPERSESSION.md plasticos_documents/business_rules/EFFECTIVE_RULES.md plasticos_documents/business_rules/EFFECTIVE_RULES.json plasticos_documents/business_rules/ALL_170_RULES_SCOPE.csv plasticos_documents/business_rules/README.md plasticos_documents/business_rules/OWNERSHIP_AND_INTEROP.md plasticos_documents/business_rules/REGISTRY.json plasticos_documents/business_rules/CROSS_DOMAIN_ACCEPTANCE.json plasticos_logistics/business_rules/SUPERSESSION.md` | `false` |
| T04 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- plasticos_logistics/business_rules/README.md plasticos_logistics/AGENTS.md plasticos_documents/business_rules/README.md plasticos_documents/AGENTS.md` | `false` |
| T05 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/contracts/test_native_first_brs_registry.py tests/contracts/test_documents_brs_registry.py` | `false` |
| T06 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- tests/contracts/` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T01 | `//tmp` | `assurance` | `Byte-for-byte preservation of all frozen BRS chapter files; changes only via dated SUPERSESSION entries with stable rule IDs`, `REGISTRY.json brs_files stays exactly [BRS-01.md..BRS-07.md] with original hashes`, `make pr is the only publication path; target branch Staging`, `Docs-and-tests only: no module version bump, no make update, no runtime activation`, `Bytes inside LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN/END in plasticos_logistics/AGENTS.md and business_rules/README.md stay unchanged; the BRS-POS-10 exception is an additive paragraph after _END plus a SUPERSESSION.md entry` | `plasticos_logistics/business_rules/BRS-01.md`, `plasticos_logistics/business_rules/BRS-02.md`, `plasticos_logistics/business_rules/BRS-03.md`, `plasticos_logistics/business_rules/BRS-04.md`, `plasticos_logistics/business_rules/BRS-05.md`, `plasticos_logistics/business_rules/BRS-06.md`, `plasticos_logistics/business_rules/BRS-07.md`, `plasticos_logistics/business_rules/REGISTRY.json`, `plasticos_documents/business_rules/BRS-POS-02-native-documents-originals-and-intake.md`, `plasticos_documents/business_rules/BRS-POS-03-evidence-classification-attribution-and-verification.md`, `plasticos_documents/business_rules/BRS-POS-09-native-documents-requests-activities-automation-and-scheduler.md`, `plasticos_logistics/models/`, `plasticos_documents/models/`, `INVARIANTS.md`, `.cursor/rules/`, `Bytes between LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN and LINDA_BRS_NATIVE_ALIGNMENT_20261026_END` |
| T02 | `plasticos_logistics/business_rules` | `docs` | `Byte-for-byte preservation of all frozen BRS chapter files; changes only via dated SUPERSESSION entries with stable rule IDs`, `REGISTRY.json brs_files stays exactly [BRS-01.md..BRS-07.md] with original hashes`, `make pr is the only publication path; target branch Staging`, `Docs-and-tests only: no module version bump, no make update, no runtime activation`, `Bytes inside LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN/END in plasticos_logistics/AGENTS.md and business_rules/README.md stay unchanged; the BRS-POS-10 exception is an additive paragraph after _END plus a SUPERSESSION.md entry` | `plasticos_logistics/business_rules/BRS-01.md`, `plasticos_logistics/business_rules/BRS-02.md`, `plasticos_logistics/business_rules/BRS-03.md`, `plasticos_logistics/business_rules/BRS-04.md`, `plasticos_logistics/business_rules/BRS-05.md`, `plasticos_logistics/business_rules/BRS-06.md`, `plasticos_logistics/business_rules/BRS-07.md`, `plasticos_logistics/business_rules/REGISTRY.json`, `plasticos_documents/business_rules/BRS-POS-02-native-documents-originals-and-intake.md`, `plasticos_documents/business_rules/BRS-POS-03-evidence-classification-attribution-and-verification.md`, `plasticos_documents/business_rules/BRS-POS-09-native-documents-requests-activities-automation-and-scheduler.md`, `plasticos_logistics/models/`, `plasticos_documents/models/`, `INVARIANTS.md`, `.cursor/rules/`, `Bytes between LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN and LINDA_BRS_NATIVE_ALIGNMENT_20261026_END` |
| T03 | `repository root` | `docs` | `Byte-for-byte preservation of all frozen BRS chapter files; changes only via dated SUPERSESSION entries with stable rule IDs`, `REGISTRY.json brs_files stays exactly [BRS-01.md..BRS-07.md] with original hashes`, `make pr is the only publication path; target branch Staging`, `Docs-and-tests only: no module version bump, no make update, no runtime activation`, `Bytes inside LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN/END in plasticos_logistics/AGENTS.md and business_rules/README.md stay unchanged; the BRS-POS-10 exception is an additive paragraph after _END plus a SUPERSESSION.md entry` | `plasticos_logistics/business_rules/BRS-01.md`, `plasticos_logistics/business_rules/BRS-02.md`, `plasticos_logistics/business_rules/BRS-03.md`, `plasticos_logistics/business_rules/BRS-04.md`, `plasticos_logistics/business_rules/BRS-05.md`, `plasticos_logistics/business_rules/BRS-06.md`, `plasticos_logistics/business_rules/BRS-07.md`, `plasticos_logistics/business_rules/REGISTRY.json`, `plasticos_documents/business_rules/BRS-POS-02-native-documents-originals-and-intake.md`, `plasticos_documents/business_rules/BRS-POS-03-evidence-classification-attribution-and-verification.md`, `plasticos_documents/business_rules/BRS-POS-09-native-documents-requests-activities-automation-and-scheduler.md`, `plasticos_logistics/models/`, `plasticos_documents/models/`, `INVARIANTS.md`, `.cursor/rules/`, `Bytes between LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN and LINDA_BRS_NATIVE_ALIGNMENT_20261026_END` |
| T04 | `repository root` | `docs` | `Byte-for-byte preservation of all frozen BRS chapter files; changes only via dated SUPERSESSION entries with stable rule IDs`, `REGISTRY.json brs_files stays exactly [BRS-01.md..BRS-07.md] with original hashes`, `make pr is the only publication path; target branch Staging`, `Docs-and-tests only: no module version bump, no make update, no runtime activation`, `Bytes inside LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN/END in plasticos_logistics/AGENTS.md and business_rules/README.md stay unchanged; the BRS-POS-10 exception is an additive paragraph after _END plus a SUPERSESSION.md entry` | `plasticos_logistics/business_rules/BRS-01.md`, `plasticos_logistics/business_rules/BRS-02.md`, `plasticos_logistics/business_rules/BRS-03.md`, `plasticos_logistics/business_rules/BRS-04.md`, `plasticos_logistics/business_rules/BRS-05.md`, `plasticos_logistics/business_rules/BRS-06.md`, `plasticos_logistics/business_rules/BRS-07.md`, `plasticos_logistics/business_rules/REGISTRY.json`, `plasticos_documents/business_rules/BRS-POS-02-native-documents-originals-and-intake.md`, `plasticos_documents/business_rules/BRS-POS-03-evidence-classification-attribution-and-verification.md`, `plasticos_documents/business_rules/BRS-POS-09-native-documents-requests-activities-automation-and-scheduler.md`, `plasticos_logistics/models/`, `plasticos_documents/models/`, `INVARIANTS.md`, `.cursor/rules/`, `Bytes between LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN and LINDA_BRS_NATIVE_ALIGNMENT_20261026_END` |
| T05 | `tests/contracts` | `assurance` | `Byte-for-byte preservation of all frozen BRS chapter files; changes only via dated SUPERSESSION entries with stable rule IDs`, `REGISTRY.json brs_files stays exactly [BRS-01.md..BRS-07.md] with original hashes`, `make pr is the only publication path; target branch Staging`, `Docs-and-tests only: no module version bump, no make update, no runtime activation`, `Bytes inside LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN/END in plasticos_logistics/AGENTS.md and business_rules/README.md stay unchanged; the BRS-POS-10 exception is an additive paragraph after _END plus a SUPERSESSION.md entry` | `plasticos_logistics/business_rules/BRS-01.md`, `plasticos_logistics/business_rules/BRS-02.md`, `plasticos_logistics/business_rules/BRS-03.md`, `plasticos_logistics/business_rules/BRS-04.md`, `plasticos_logistics/business_rules/BRS-05.md`, `plasticos_logistics/business_rules/BRS-06.md`, `plasticos_logistics/business_rules/BRS-07.md`, `plasticos_logistics/business_rules/REGISTRY.json`, `plasticos_documents/business_rules/BRS-POS-02-native-documents-originals-and-intake.md`, `plasticos_documents/business_rules/BRS-POS-03-evidence-classification-attribution-and-verification.md`, `plasticos_documents/business_rules/BRS-POS-09-native-documents-requests-activities-automation-and-scheduler.md`, `plasticos_logistics/models/`, `plasticos_documents/models/`, `INVARIANTS.md`, `.cursor/rules/`, `Bytes between LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN and LINDA_BRS_NATIVE_ALIGNMENT_20261026_END` |
| T06 | `tests` | `assurance` | `Byte-for-byte preservation of all frozen BRS chapter files; changes only via dated SUPERSESSION entries with stable rule IDs`, `REGISTRY.json brs_files stays exactly [BRS-01.md..BRS-07.md] with original hashes`, `make pr is the only publication path; target branch Staging`, `Docs-and-tests only: no module version bump, no make update, no runtime activation`, `Bytes inside LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN/END in plasticos_logistics/AGENTS.md and business_rules/README.md stay unchanged; the BRS-POS-10 exception is an additive paragraph after _END plus a SUPERSESSION.md entry` | `plasticos_logistics/business_rules/BRS-01.md`, `plasticos_logistics/business_rules/BRS-02.md`, `plasticos_logistics/business_rules/BRS-03.md`, `plasticos_logistics/business_rules/BRS-04.md`, `plasticos_logistics/business_rules/BRS-05.md`, `plasticos_logistics/business_rules/BRS-06.md`, `plasticos_logistics/business_rules/BRS-07.md`, `plasticos_logistics/business_rules/REGISTRY.json`, `plasticos_documents/business_rules/BRS-POS-02-native-documents-originals-and-intake.md`, `plasticos_documents/business_rules/BRS-POS-03-evidence-classification-attribution-and-verification.md`, `plasticos_documents/business_rules/BRS-POS-09-native-documents-requests-activities-automation-and-scheduler.md`, `plasticos_logistics/models/`, `plasticos_documents/models/`, `INVARIANTS.md`, `.cursor/rules/`, `Bytes between LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN and LINDA_BRS_NATIVE_ALIGNMENT_20261026_END` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.resolve_documents_and_logistics_brs_drift.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.resolve_documents_and_logistics_brs_drift.v1` |
| source_execution_ref | `plan.simple.resolve_documents_and_logistics_brs_drift.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (sha256 of extracted chapter equals its SHA256SUMS line) → blocked; try the Dropbox pack copy verified against its SHA256SUMS; if neither verifies, stop and ask the operator for the v1.0.0 source; C2 fails (git diff shows zero byte changes to BRS-01..07.md, REGISTRY.json, and the three Documents chapter files) → revert the touched frozen file; redo via supersession text only; C3 fails (V1, V2, V3, V4 all pass locally) → fix or revert before make pr; do not publish red |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | git restore the touched business_rules, AGENTS.md, and tests/contracts paths; delete the two new files; nothing else moves and no module upgrade occurred |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `python3 -m pytest tests/contracts/test_native_first_brs_registry.py tests/contracts/test_logistics_brs_registry.py tests/contracts/test_documents_brs_registry.py -q`
- re-run `ruff check tests/contracts && ruff format --check tests/contracts`
- re-run `.pre-commit-config.yaml`
- re-run `make pr`
- re-run `python3 -m pytest tests/contracts/test_native_first_brs_registry.py -q`
- re-run `python3 -m pytest tests/contracts/test_logistics_brs_registry.py -q`
- re-run `python3 -m pytest tests/contracts/test_documents_brs_registry.py -q`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` — highest todo risk across 6 todo(s) |
| uncertainty | `medium` — 1 unknown(s), 0 blocking |
| blast_radius | `medium` — Documentation trees of two modules plus tests/contracts; no runtime model, view, or manifest changes; worst case is a red contract test or a broken preservation gate caught locally before make pr |
| architectural_boundaries_crossed | `plasticos_documents business_rules <-> plasticos_logistics business_rules (documentation ownership only)` |
| external_systems_touched | none |
| migration_required | `false` |
| unknown_dependency_count | `1` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.resolve_documents_and_logistics_brs_drift.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.resolve_documents_and_logistics_brs_drift.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T01 | Resolve the stash by subject, not by index alone. Require stash@{8} subject 'remaining untracked before leaving only Staging (2026-11-01)'; if the subject differs, search stashes for that subject and stop if it is absent. Extract RULES/BRS-POS-10-linda-logistics-commercial-and-physical-communication.md, SHA256SUMS, and the covering REGISTRY/rules.json rows via git show '<stash>^3:docs/campaigns/10-26-26/PlasticOS_Native_First_BRS_v1.0.0_2026-10-25/...' to /tmp/brs-pos-10-extract/. Verify the chapter sha256 against SHA256SUMS. Never pop or apply the stash. Mismatch or missing blob: blocked, stop. Fallback only: /Users/ib-mac/Dropbox/Downloads (DBOX)/PlasticOS_Native_First_BRS_v1.0.0_2026-10-25/ verified against its SHA256SUMS. Read tests/contracts/test_logistics_brs_registry.py fully before T02. | Cursor Build agent | `medium` | S | `[]` | `/tmp/brs-pos-10-extract/` |
| T02 | Install the chapter byte-for-byte as plasticos_logistics/business_rules/BRS-POS-10-linda-logistics-commercial-and-physical-communication.md. Create NATIVE_FIRST_REGISTRY.json beside it: source pack name and version, chapter sha256 from SHA256SUMS, the 16 rule IDs with titles and scope classes from plasticos_documents/business_rules/ALL_170_RULES_SCOPE.csv rows 129-144, install date, and a statement that this installs one chapter without admitting the other eleven Native-First chapters. Do not touch plasticos_logistics/business_rules/REGISTRY.json. Documents REGISTRY.json is T03 only, and only for the ownership_transferred list. | Cursor Build agent | `medium` | S | `[T01]` | `plasticos_logistics/business_rules/BRS-POS-10-linda-logistics-commercial-and-physical-communication.md`, `plasticos_logistics/business_rules/NATIVE_FIRST_REGISTRY.json` |
| T03 | Transfer external-send ownership of BRS-POS-09-R006..R012 by dated supersession, without treating installed text as deleted. Exact titles from ALL_170_RULES_SCOPE.csv: R006 Only one external reminder writer; R007 Supplier document business clock; R008 Carrier document business clock; R009 Buyer document business clock; R010 No duplicate daily touch; R011 Quiet hours and locale aware deadlines; R012 Stop on verified or inapplicable. Documents: dated SUPERSESSION.md entry; set EFFECTIVE_RULES.md/.json semantic_owner of those seven to plasticos_logistics (external send) while Documents keeps status/activity supply; reclassify the seven CSV rows from DOCUMENTS_BRS_LOCAL to CROSS_DOMAIN_CONSUMER_REFERENCE. Do not change REGISTRY.json source_rule_ids or local_rule_count (both stay 44) or external_rule_count (stays 126): 44+126=170 counts installed verbatim text, not current owner. Add ownership_transferred listing the seven IDs and the logistics owner. Rewrite README.md and OWNERSHIP_AND_INTEROP.md so they stop saying all 44 are Documents-owned: 44 installed verbatim, 37 remain Documents-owned, seven external-send owners moved. CROSS_DOMAIN_ACCEPTANCE.json: one owner note that AC-DOC-X10, X11, X12 (and any other case citing these IDs) still test the rule text but the external sender is logistics; do not change positive_expected or result (they stay NOT_RUN). Chapter bytes unchanged. Logistics SUPERSESSION.md: matching dated admission, cross-referenced to BRS-02-R007, BRS-06-R039, BRS-07-R051. Grep tests/ and ci/ for a literal assertion of 44 Documents-owned rules before committing. | Cursor Build agent | `medium` | M | `[T02]` | `plasticos_documents/business_rules/SUPERSESSION.md`, `plasticos_documents/business_rules/EFFECTIVE_RULES.md`, `plasticos_documents/business_rules/EFFECTIVE_RULES.json`, `plasticos_documents/business_rules/ALL_170_RULES_SCOPE.csv`, `plasticos_documents/business_rules/README.md`, `plasticos_documents/business_rules/OWNERSHIP_AND_INTEROP.md`, `plasticos_documents/business_rules/REGISTRY.json`, `plasticos_documents/business_rules/CROSS_DOMAIN_ACCEPTANCE.json`, `plasticos_logistics/business_rules/SUPERSESSION.md` |
| T04 | Wire agent bindings outside the preserved overlay markers. Do not edit bytes between LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN and _END in plasticos_logistics/AGENTS.md or business_rules/README.md. Those blocks say BRS-POS-* is reference-only and not a second copied authority. After each _END marker, add one paragraph: the dated supersession admits exactly one copied chapter, BRS-POS-10, and admits BRS-POS-09-R006..R012 as Linda external-send obligations; every other BRS-POS chapter stays a cross-domain reference. Add the same two items to the read-first list that already sits above the marker in AGENTS.md. Documents README.md and plasticos_documents/AGENTS.md: one sentence plus pointer that external-send ownership of the seven IDs moved, and that 44 still means installed text. Both packs keep the statement that BRS-POS-04..08 and 11..12 stay with their owners. | Cursor Build agent | `low` | S | `[T03]` | `plasticos_logistics/business_rules/README.md`, `plasticos_logistics/AGENTS.md`, `plasticos_documents/business_rules/README.md`, `plasticos_documents/AGENTS.md` |
| T05 | Contract tests. tests/contracts/test_native_first_brs_registry.py: installed chapter sha256 equals NATIVE_FIRST_REGISTRY.json and the source SHA256SUMS line; 16 headings match registry IDs. tests/contracts/test_documents_brs_registry.py: ALL_170_RULES_SCOPE.csv has exactly 37 DOCUMENTS_BRS_LOCAL rows; the seven IDs are CROSS_DOMAIN_CONSUMER_REFERENCE; EFFECTIVE_RULES.json semantic_owner for those seven is plasticos_logistics; REGISTRY.json source_rule_ids length and local_rule_count stay 44 and external_rule_count stays 126; ownership_transferred lists the seven; the three chapter files are byte-unchanged against recorded hashes; logistics and documents AGENTS.md/README.md contain the post-marker exception paragraph and do not differ inside the 2026-10-26 marker blocks from HEAD. Do not modify the original assertions in test_logistics_brs_registry.py. | Cursor Build agent | `low` | M | `[T02, T03]` | `tests/contracts/test_native_first_brs_registry.py`, `tests/contracts/test_documents_brs_registry.py` |
| T06 | Gate and publish. ruff check --fix and ruff format on the new test files; run the three contract test files with pytest; then scoped commit of exactly this plan's file list and make pr into Staging (stack on the open PR chain tip when one exists). Docs-plus-pure-tests scope: pr_check_scope skips Docker smoke. | Cursor Build agent | `low` | S | `[T04, T05]` | `tests/contracts/` |

**Critical path:** T01 → T02 → T03 → T05 → T06

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | Verbatim BRS-POS-10 chapter recovered and hash-verified from stash@{8} | installation with provenance |
| M2 | Chapter installed in logistics and seven BRS-POS-09 clauses transferred by supersession in both packs | wiring and tests |
| M3 | Agent bindings wired and contract tests green alongside the untouched logistics preservation gate | publication via make pr |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | sha256 of extracted chapter equals its SHA256SUMS line | blocked; try the Dropbox pack copy verified against its SHA256SUMS; if neither verifies, stop and ask the operator for the v1.0.0 source |
| C2 | M2 | git diff shows zero byte changes to BRS-01..07.md, REGISTRY.json, and the three Documents chapter files | revert the touched frozen file; redo via supersession text only |
| C3 | M3 | V1, V2, V3, V4 all pass locally | fix or revert before make pr; do not publish red |

### Leverage

- **Ranked todos:** `T02`, `T01`, `T03`, `T04`, `T05`, `T06`
- **Shared causes:** The Native-First pack was never committed, so its logistics chapter has no in-tree home and its ownership rows were filed by whoever held the pack (Documents); Both packs already carry the supersession mechanism, so ownership relocation needs no new architecture
- **Deletions / consolidations:** Seven ALL_170_RULES_SCOPE.csv rows reclassified instead of duplicating rule text into logistics; No second copy of any chapter: one new file total

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| plasticos_logistics/AGENTS.md and plasticos_documents/AGENTS.md | `update` | `T04` | — |
| root AGENTS.md / CLAUDE.md | `n_a` | — | module-local BRS wiring; the root logistics BRS paragraph already points at plasticos_logistics/business_rules/, which remains the home |
| INVARIANTS.md | `n_a` | — | no invariant text changes; invariant/rule drift is owned by the separate agent-rule realignment plan |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01 | `quality_gate_evidence` | command | `python3 -m pytest tests/contracts/test_native_first_brs_registry.py -q` | pass; includes assertion that installed chapter sha256 equals the source SHA256SUMS value recorded in NATIVE_FIRST_REGISTRY.json | `not_run` |
| E-V2 | SP-03 | `quality_gate_evidence` | command | `python3 -m pytest tests/contracts/test_logistics_brs_registry.py -q` | pass with the original BRS-01..07 assertions unmodified | `not_run` |
| E-V3 | SP-02, SP-04 | `quality_gate_evidence` | command | `python3 -m pytest tests/contracts/test_documents_brs_registry.py -q` | pass; 37 DOCUMENTS_BRS_LOCAL rows; seven IDs cross-domain; semantic_owner plasticos_logistics; REGISTRY source_rule_ids and local_rule_count remain 44; external_rule_count remains 126; chapter bytes unchanged; post-marker exception paragraph present in logistics and documents AGENTS.md and README.md; bytes inside the 2026-10-26 markers unchanged versus HEAD | `not_run` |
| E-V4 | SP-05 | `quality_gate_evidence` | command | `ruff check tests/contracts && ruff format --check tests/contracts` | clean | `not_run` |
| E-V5 | SP-05 | `quality_gate_evidence` | command | `make pr` | local gate green (pre-commit catalog .pre-commit-config.yaml), PR opened into Staging, PR URL displayed | `not_run` |
| E-V6 | regression gate (no SP) | `quality_gate_evidence` | command | `.pre-commit-config.yaml` | pre-commit run --all-files clean on the committed change set (runs inside make pr local gate) | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Does adding BRS-POS-10 to the logistics pack break the hash-locked registry test? Only if REGISTRY.json brs_files is touched; the plan uses a separate NATIVE_FIRST_REGISTRY.json and C2 proves zero frozen-byte diffs.
- Does transferring the seven clauses without moving chapter bytes leave Documents self-contradictory? No; OWNERSHIP_AND_INTEROP.md already names Linda the only external sender, and the scope CSV plus EFFECTIVE_RULES owners become consistent with it.
- Is stash@{8} still intact at execution time, and does its SHA256SUMS still verify? If not, the Dropbox copy is the only admitted fallback and C1 blocks otherwise.
- Could another agent's dirty working-tree edits to load.py/freight files bleed into this commit? Scoped commit of only the plan's file list prevents it.
- Does keeping local_rule_count at 44 while the scope CSV drops to 37 Documents-owned rows split the registry? No: 44+126=170 counts installed verbatim text. Ownership of the seven IDs lives in ownership_transferred, the scope CSV, and SUPERSESSION.md. T05 asserts both numbers.

### Assumption failure conditions

- Assumed false if the stash chapter hash does not match SHA256SUMS (source corrupted): plan blocks at C1
- Assumed false if test_logistics_brs_registry.py asserts anything about extra files in business_rules/ beyond the brs_files list (would reject the new chapter): T01 reads the test fully before T02
- Assumed false if the BRS-POS-09 chapter text itself forbids ownership transfer by supersession: T03 reads rows R006..R012 in the chapter first

### Blast radius notes

- Documentation trees of two modules plus tests/contracts; no runtime model, view, or manifest changes; worst case is a red contract test or a broken preservation gate caught locally before make pr

### Rollback constraints

- git restore the touched business_rules, AGENTS.md, and tests/contracts paths; delete the two new files; nothing else moves and no module upgrade occurred

### Risks

| risk | mitigation |
|------|------------|
| stash@{8} dropped or rewritten before execution | C1 fallback to the verified Dropbox pack copy; otherwise block and ask |
| Hidden consumer asserts the Documents 44-local-rule count or the exact scope CSV rows | grep for '44' and the seven rule IDs across tests/ and ci/ before committing T03 |
| README.md edit lands inside the preserved 2026-10-26 overlay markers | additive section strictly outside the marked block; C2 diff review |
| BAN001 banned identifier appearing in new files | make pr-check runs ban-check; review new file text in T05 |

## Out of scope

- Bytes of the seven frozen BRS-01..07.md chapters and plasticos_logistics/business_rules/REGISTRY.json brs_files list (hash-locked by contract test)
- Bytes of the three Documents chapter files BRS-POS-02/03/09-*.md
- Any addon Python/XML/manifest runtime code (docs-and-tests only; no version bump per rule 89)
- INVARIANTS.md, .cursor/rules, and the Partners-first plan (separate plans own those)
- Installing BRS-POS-04..08, 11, 12 anywhere (owners are transaction/commercial, Inventory/Purchase/Sales, purchase/sales/claims/accounting, security/sequencing)
- Live mail, cron, or any runtime activation of the relocated rules
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.resolve_documents_and_logistics_brs_drift.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.resolve_documents_and_logistics_brs_drift.v1` |
| source_ref | `plan.simple.resolve_documents_and_logistics_brs_drift.v1` |
| current_state | `draft` |
| implementation_ready | `false` |

### Gates

- **executable_when:**
  - baseline locked + reverified
  - blocking capability probes pass
  - DAG acyclic
  - envelope + side-effect matrix complete for mutate todos
  - no blocking unknowns
- **complete_when:**
  - all blocking success-property evidence `passed`
  - rollback contract still valid / unused-or-verified
  - out_of_scope respected (diff hygiene)
- **blocking_conditions:**
  - `preflight_blocked`
  - envelope breach
  - baseline drift
  - failed blocking property

### Evidence

- **required_evidence_refs:** E-V1, E-V2, E-V3, E-V4, E-V5, E-V6
- **observed_evidence_refs:** none
- **missing_evidence:** E-V1, E-V2, E-V3, E-V4, E-V5, E-V6

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `unknown` | U1 | Does the BRS-POS-10 chapter blob in the named stash match its SHA256SUMS line? P1 listed the path only. — T02 is blocked until C1 compares the bytes. No chapter text may be reconstructed from CSV titles. | `probe` |
| `open_blocker` | stop_reason | Recursive Alignment bound. Plan contract revised in place. Execution awaits Build. U1 chapter hash not yet probed. | planning convergence `partial` |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `executable_when` |
| minimum_safe_next_action | When law holds and status=`executable`, press **Build**, stack if any open PR exists (`PR_STACK=auto`), then `make pr` and display the PR URL — do not free-form execute |
| execute_via | Cursor Build; stacked PR if any open PR exists; display PR URL |
| next_skill | Build then stacked make pr |
| broader_work_requires_separate_contract | `true` |

---

## Machine stub (optional YAML instance seed)

Projected from PLAN_DOCUMENT; keep in sync with the sections above.

```yaml
schema_id: "canonical.schema.plan_document.v1"
schema_version: "1.0.0"
metadata:
  plan_id: "plan.simple.resolve_documents_and_logistics_brs_drift.v1"
  name: "Resolve Documents and Logistics BRS drift"
  overview: "Relocate the Linda-owned Native-First BRS material so each rule set sits with its concern: install the BRS-POS-10 chapter verbatim into plasticos_logistics/business_rules with recorded provenance, transfer ownership of BRS-POS-09-R006..R012 to plasticos_logistics by dated supersession entries in both packs without rewriting any frozen chapter bytes, then wire both packs into their modules via README/AGENTS read-first lists, registries, and hash-locked contract tests. Alignment auditor: .cursor-commands/kernels/Recursive Alignment.md (recursive_architecture_alignment_auditor 1.0), audit-only except this authorized in-place plan revision."
  status: "draft"
  is_project: false
  owner: "igor_beylin"
architect_framing:
  planning_ssot: "PLAN_DOCUMENT"
  plan_class: "bounded_execution_contract"
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: "cryptoxdog/IB-Odoo_19"
  commit_sha: "077ffad4a2825db41b5fcea65a013812129b05ab"
  dirty: "false"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "Relocate the Linda-owned Native-First BRS material so each rule set sits with its concern: install the BRS-POS-10 chapter verbatim into plasticos_logistics/business_rules with recorded provenance, transfer ownership of BRS-POS-09-R006..R012 to plasticos_logistics by dated supersession entries in both packs without rewriting any frozen chapter bytes, then wire both packs into their modules via README/AGENTS read-first lists, registries, and hash-locked contract tests. Alignment auditor: .cursor-commands/kernels/Recursive Alignment.md (recursive_architecture_alignment_auditor 1.0), audit-only except this authorized in-place plan revision."
  success_properties:
    - id: "SP-01"
      property: "BRS-POS-10 chapter installed byte-identical to the source pack with sha256 provenance recorded in NATIVE_FIRST_REGISTRY.json and proven by V1"
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "Seven BRS-POS-09 clauses (R006..R012) owned by plasticos_logistics via dated supersession in both packs with Documents chapter bytes unchanged, proven by V3"
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
    - id: "SP-03"
      property: "Existing logistics preservation gate unbroken: original BRS-01..07 assertions in test_logistics_brs_registry.py pass unmodified, proven by V2"
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
    - id: "SP-04"
      property: "Agent routing wired without contradicting the preserved 2026-10-26 overlays: an additive paragraph after each LINDA_BRS_NATIVE_ALIGNMENT_20261026_END marker names BRS-POS-10 and BRS-POS-09-R006..R012 as the only admitted exception, proven by V3 assertions that read those paragraphs"
      evidence_type: "quality_gate"
      proof: ["V3"]
      blocking: true
    - id: "SP-05"
      property: "Lint and repo gates green on the new test files, proven by V4 and V5"
      evidence_type: "quality_gate"
      proof: ["V4", "V5"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.resolve_documents_and_logistics_brs_drift.v1"
execution_envelope:
  filesystem:
    write_allow: ["plasticos_logistics/business_rules/BRS-POS-10-linda-logistics-commercial-and-physical-communication.md", "plasticos_logistics/business_rules/NATIVE_FIRST_REGISTRY.json", "plasticos_logistics/business_rules/README.md", "plasticos_logistics/business_rules/SUPERSESSION.md", "plasticos_logistics/AGENTS.md", "plasticos_documents/business_rules/SUPERSESSION.md", "plasticos_documents/business_rules/EFFECTIVE_RULES.md", "plasticos_documents/business_rules/EFFECTIVE_RULES.json", "plasticos_documents/business_rules/ALL_170_RULES_SCOPE.csv", "plasticos_documents/business_rules/README.md", "plasticos_documents/AGENTS.md", "tests/contracts/test_native_first_brs_registry.py", "tests/contracts/test_documents_brs_registry.py", "tests/contracts/test_logistics_brs_registry.py", "plasticos_documents/business_rules/OWNERSHIP_AND_INTEROP.md", "plasticos_documents/business_rules/REGISTRY.json", "plasticos_documents/business_rules/CROSS_DOMAIN_ACCEPTANCE.json"]
    write_deny: ["plasticos_logistics/business_rules/BRS-01.md", "plasticos_logistics/business_rules/BRS-02.md", "plasticos_logistics/business_rules/BRS-03.md", "plasticos_logistics/business_rules/BRS-04.md", "plasticos_logistics/business_rules/BRS-05.md", "plasticos_logistics/business_rules/BRS-06.md", "plasticos_logistics/business_rules/BRS-07.md", "plasticos_logistics/business_rules/REGISTRY.json", "plasticos_documents/business_rules/BRS-POS-02-native-documents-originals-and-intake.md", "plasticos_documents/business_rules/BRS-POS-03-evidence-classification-attribution-and-verification.md", "plasticos_documents/business_rules/BRS-POS-09-native-documents-requests-activities-automation-and-scheduler.md", "plasticos_logistics/models/", "plasticos_documents/models/", "INVARIANTS.md", ".cursor/rules/", "Bytes between LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN and LINDA_BRS_NATIVE_ALIGNMENT_20261026_END"]
  commands:
    allow: ["python3 -m pytest tests/contracts/test_native_first_brs_registry.py tests/contracts/test_logistics_brs_registry.py tests/contracts/test_documents_brs_registry.py -q", "ruff check tests/contracts && ruff format --check tests/contracts", ".pre-commit-config.yaml", "make pr", "python3 -m pytest tests/contracts/test_native_first_brs_registry.py -q", "python3 -m pytest tests/contracts/test_logistics_brs_registry.py -q", "python3 -m pytest tests/contracts/test_documents_brs_registry.py -q"]
  network:
    mode: "named_services_only"
  secrets:
    access: "none"
    redaction_required: true
  autonomous_merge: false
side_effects_and_idempotency:
  - todo_id: "T01"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T02"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T03"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T04"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T05"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T06"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
rollback_contract_ref: "rollback.plan.simple.resolve_documents_and_logistics_brs_drift.v1"
dependency_topology_ref: "dag.plan.simple.resolve_documents_and_logistics_brs_drift.v1"
validation_evidence_refs: ["E-V1", "E-V2", "E-V3", "E-V4", "E-V5", "E-V6"]
stress_and_disconfirm:
  disconfirming_cases: ["Does adding BRS-POS-10 to the logistics pack break the hash-locked registry test? Only if REGISTRY.json brs_files is touched; the plan uses a separate NATIVE_FIRST_REGISTRY.json and C2 proves zero frozen-byte diffs.", "Does transferring the seven clauses without moving chapter bytes leave Documents self-contradictory? No; OWNERSHIP_AND_INTEROP.md already names Linda the only external sender, and the scope CSV plus EFFECTIVE_RULES owners become consistent with it.", "Is stash@{8} still intact at execution time, and does its SHA256SUMS still verify? If not, the Dropbox copy is the only admitted fallback and C1 blocks otherwise.", "Could another agent's dirty working-tree edits to load.py/freight files bleed into this commit? Scoped commit of only the plan's file list prevents it.", "Does keeping local_rule_count at 44 while the scope CSV drops to 37 Documents-owned rows split the registry? No: 44+126=170 counts installed verbatim text. Ownership of the seven IDs lives in ownership_transferred, the scope CSV, and SUPERSESSION.md. T05 asserts both numbers."]
  assumption_failure_conditions: ["Assumed false if the stash chapter hash does not match SHA256SUMS (source corrupted): plan blocks at C1", "Assumed false if test_logistics_brs_registry.py asserts anything about extra files in business_rules/ beyond the brs_files list (would reject the new chapter): T01 reads the test fully before T02", "Assumed false if the BRS-POS-09 chapter text itself forbids ownership transfer by supersession: T03 reads rows R006..R012 in the chapter first"]
out_of_scope: ["Bytes of the seven frozen BRS-01..07.md chapters and plasticos_logistics/business_rules/REGISTRY.json brs_files list (hash-locked by contract test)", "Bytes of the three Documents chapter files BRS-POS-02/03/09-*.md", "Any addon Python/XML/manifest runtime code (docs-and-tests only; no version bump per rule 89)", "INVARIANTS.md, .cursor/rules, and the Partners-first plan (separate plans own those)", "Installing BRS-POS-04..08, 11, 12 anywhere (owners are transaction/commercial, Inventory/Purchase/Sales, purchase/sales/claims/accounting, security/sequencing)", "Live mail, cron, or any runtime activation of the relocated rules"]
convergence_contract_ref: "conv.plan.simple.resolve_documents_and_logistics_brs_drift.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T01"
    content: "Resolve the stash by subject, not by index alone. Require stash@{8} subject 'remaining untracked before leaving only Staging (2026-11-01)'; if the subject differs, search stashes for that subject and stop if it is absent. Extract RULES/BRS-POS-10-linda-logistics-commercial-and-physical-communication.md, SHA256SUMS, and the covering REGISTRY/rules.json rows via git show '<stash>^3:docs/campaigns/10-26-26/PlasticOS_Native_First_BRS_v1.0.0_2026-10-25/...' to /tmp/brs-pos-10-extract/. Verify the chapter sha256 against SHA256SUMS. Never pop or apply the stash. Mismatch or missing blob: blocked, stop. Fallback only: /Users/ib-mac/Dropbox/Downloads (DBOX)/PlasticOS_Native_First_BRS_v1.0.0_2026-10-25/ verified against its SHA256SUMS. Read tests/contracts/test_logistics_brs_registry.py fully before T02."
    status: "pending"
  - id: "T02"
    content: "Install the chapter byte-for-byte as plasticos_logistics/business_rules/BRS-POS-10-linda-logistics-commercial-and-physical-communication.md. Create NATIVE_FIRST_REGISTRY.json beside it: source pack name and version, chapter sha256 from SHA256SUMS, the 16 rule IDs with titles and scope classes from plasticos_documents/business_rules/ALL_170_RULES_SCOPE.csv rows 129-144, install date, and a statement that this installs one chapter without admitting the other eleven Native-First chapters. Do not touch plasticos_logistics/business_rules/REGISTRY.json. Documents REGISTRY.json is T03 only, and only for the ownership_transferred list."
    status: "pending"
  - id: "T03"
    content: "Transfer external-send ownership of BRS-POS-09-R006..R012 by dated supersession, without treating installed text as deleted. Exact titles from ALL_170_RULES_SCOPE.csv: R006 Only one external reminder writer; R007 Supplier document business clock; R008 Carrier document business clock; R009 Buyer document business clock; R010 No duplicate daily touch; R011 Quiet hours and locale aware deadlines; R012 Stop on verified or inapplicable. Documents: dated SUPERSESSION.md entry; set EFFECTIVE_RULES.md/.json semantic_owner of those seven to plasticos_logistics (external send) while Documents keeps status/activity supply; reclassify the seven CSV rows from DOCUMENTS_BRS_LOCAL to CROSS_DOMAIN_CONSUMER_REFERENCE. Do not change REGISTRY.json source_rule_ids or local_rule_count (both stay 44) or external_rule_count (stays 126): 44+126=170 counts installed verbatim text, not current owner. Add ownership_transferred listing the seven IDs and the logistics owner. Rewrite README.md and OWNERSHIP_AND_INTEROP.md so they stop saying all 44 are Documents-owned: 44 installed verbatim, 37 remain Documents-owned, seven external-send owners moved. CROSS_DOMAIN_ACCEPTANCE.json: one owner note that AC-DOC-X10, X11, X12 (and any other case citing these IDs) still test the rule text but the external sender is logistics; do not change positive_expected or result (they stay NOT_RUN). Chapter bytes unchanged. Logistics SUPERSESSION.md: matching dated admission, cross-referenced to BRS-02-R007, BRS-06-R039, BRS-07-R051. Grep tests/ and ci/ for a literal assertion of 44 Documents-owned rules before committing."
    status: "pending"
  - id: "T04"
    content: "Wire agent bindings outside the preserved overlay markers. Do not edit bytes between LINDA_BRS_NATIVE_ALIGNMENT_20261026_BEGIN and _END in plasticos_logistics/AGENTS.md or business_rules/README.md. Those blocks say BRS-POS-* is reference-only and not a second copied authority. After each _END marker, add one paragraph: the dated supersession admits exactly one copied chapter, BRS-POS-10, and admits BRS-POS-09-R006..R012 as Linda external-send obligations; every other BRS-POS chapter stays a cross-domain reference. Add the same two items to the read-first list that already sits above the marker in AGENTS.md. Documents README.md and plasticos_documents/AGENTS.md: one sentence plus pointer that external-send ownership of the seven IDs moved, and that 44 still means installed text. Both packs keep the statement that BRS-POS-04..08 and 11..12 stay with their owners."
    status: "pending"
  - id: "T05"
    content: "Contract tests. tests/contracts/test_native_first_brs_registry.py: installed chapter sha256 equals NATIVE_FIRST_REGISTRY.json and the source SHA256SUMS line; 16 headings match registry IDs. tests/contracts/test_documents_brs_registry.py: ALL_170_RULES_SCOPE.csv has exactly 37 DOCUMENTS_BRS_LOCAL rows; the seven IDs are CROSS_DOMAIN_CONSUMER_REFERENCE; EFFECTIVE_RULES.json semantic_owner for those seven is plasticos_logistics; REGISTRY.json source_rule_ids length and local_rule_count stay 44 and external_rule_count stays 126; ownership_transferred lists the seven; the three chapter files are byte-unchanged against recorded hashes; logistics and documents AGENTS.md/README.md contain the post-marker exception paragraph and do not differ inside the 2026-10-26 marker blocks from HEAD. Do not modify the original assertions in test_logistics_brs_registry.py."
    status: "pending"
  - id: "T06"
    content: "Gate and publish. ruff check --fix and ruff format on the new test files; run the three contract test files with pytest; then scoped commit of exactly this plan's file list and make pr into Staging (stack on the open PR chain tip when one exists). Docs-plus-pure-tests scope: pr_check_scope skips Docker smoke."
    status: "pending"
```

## Build evidence (auto)

- detected_at: `2026-11-05T17:21:45Z`
- conversation_id: `abfd46db-27d0-4fc8-9098-55431bbdbd7a`
- generation_id: `2b5e78ec-cdf6-4b68-8fa5-1fff6500ecdd`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/abfd46db-27d0-4fc8-9098-55431bbdbd7a/abfd46db-27d0-4fc8-9098-55431bbdbd7a.jsonl`
- todos at build time:
- `T01`: completed
- `T02`: completed
- `T03`: completed
- `T04`: completed
- `T05`: completed
- `T06`: completed
