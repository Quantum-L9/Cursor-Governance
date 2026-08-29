# Donor Harvest Brief — intelligence/_archived → https://github.com/Quantum-L9/Cursor-Governance [Suite-6 intelligence archive seams, successors, and transferable semantics]

## Executive Picture
Status: PARTIAL. Highest-leverage nugget: c-cutover-seam-closure.

## Source Identity
```json
{'archive_commit': '268608be', 'archive_date': '2026-07-19', 'archive_subject': 'chore(governance): archive Suite-6 legacy files, migrate wire_executor, add repo root config', 'file_count': 9, 'inventory_status': 'PASS', 'kind': 'directory', 'path': '/Users/ib-mac/Cursor-Governance/intelligence/_archived', 'suite6_cutover': True}
```

## Inventory
- improvement-loop.md | archive
- meta-audit.md | archive
- core-rules.md | archive
- workspace/setup-new-workspace.md | archive
- workspace/setup-new-workspace.py | archive
- learning/auto_calibrator.py | archive
- learning/feedback_collector.py | archive
- learning/chat-learning-extractor.py | archive
- context-memory/context-extractor.py | archive

## System Reconstruction
```json
{'control_flow': [{'from': 'workspace/setup-new-workspace.py', 'relation': 'wraps (retired)', 'to': 'environment/env-manager.py + ops/scripts/setup_workspace_symlinks.sh + process_learnings.sh + process_context.sh'}, {'from': 'ops/scripts/process_context.sh', 'relation': 'still invokes missing live path', 'to': 'intelligence/context-memory/context-extractor.py (now intelligence/_archived/context-memory/)'}, {'from': 'context-extractor.py', 'relation': 'intended-but-never-wired replacement', 'to': 'intelligence/context-memory/graphiti_sink.py'}, {'from': 'feedback_collector.py + auto_calibrator.py', 'relation': 'write', 'to': 'foundation/logic/rule-registry.json (now foundation/_archived/logic/)'}, {'from': 'chat-learning-extractor.py + auto_calibrator.py', 'relation': 'append', 'to': 'intelligence/meta-learning/meta-learning-log.md'}, {'from': 'improvement-loop.md', 'relation': 'cites absent', 'to': 'ops/reasoning-metrics.md and intelligence/meta-audit.md'}], 'dependencies': [{'name': 'foundation/logic/probabilistic_engine.py', 'state': 'archived', 'used_by': 'context-extractor Bayesian gate, auto_calibrator'}, {'name': 'Cursor User/workspaceStorage state.vscdb composer.composerData', 'state': 'superseded by ~/.cursor/projects jsonl + sessionEnd archive_transcript', 'used_by': 'context-extractor.py'}, {'name': 'Dropbox Cursor Governance / L9 Governance (L9)', 'state': 'forbidden SSOT fallback', 'used_by': 'setup-new-workspace.md/.py'}, {'name': 'LaunchAgents com.tenx.chat-export / com.tenx.learning-processor', 'state': 'retired 2026-08-13', 'used_by': 'setup-new-workspace.py Phase 7'}], 'identity': {'epistemic': 'CONFIRMED', 'name': 'Suite-6 Governance Intelligence Layer (archived)', 'summary': 'Nine leftover artifacts from the 10X/Suite-6 intelligence layer, archived 2026-07-19 (268608be) as part of the Post-Suite-6 / Graphiti-native cut-over. Headers still claim status=active. Live successors are SessionStart, Graphiti hydrate/PICKUP, sessionEnd transcript archive, make improve, and setup_workspace_symlinks.sh.'}, 'must_not_own': ['Graphiti group_id / write authority', 'SessionStart activation', 'workspace symlink law', 'make improve / L4 release', 'S3 transcript archive policy', 'ECE as a reasoning or confidence gate', 'rule-registry.json mutation', 'Dropbox or .suite6-config.json reactivation', 'n8n start-up kit as governance prerequisite'], 'ownership_boundaries': [{'owner': 'AGENTS.md SessionStart + ops/hooks/session_start_bootstrap.sh', 'owns': 'workspace activation; forbids 22-file dump and Dropbox SSOT'}, {'owner': 'ops/graphiti/hydration + graphiti_memory_client.py', 'owns': 'resume packets, PICKUP, sessionEnd transcript archive to S3'}, {'owner': 'make improve + kernels + L4 receipts', 'owns': 'observe-align-validate-record improvement cycle'}, {'owner': 'intelligence/_archived', 'owns': 'Suite-6 evidence only; no execution authority'}, {'owner': 'CANONICAL_LAW.md §8', 'owns': 'memory-layer declaration; still names graphiti_sink.py as durable-episode interface'}], 'workflows': [{'evidence_ids': ['e-setup-md-header', 'e-setup-py-launchd'], 'id': 'suite6-workspace-enable', 'steps': ['preflight Dropbox/L9 path + yaml', 'env-manager sync writes .suite6-config.json', 'symlink .cursor-commands', 'mandate 22+ file session read', 'activate process_learnings.sh + process_context.sh', 'verify LaunchAgents com.tenx.* and Suite-6 headers']}, {'evidence_ids': ['e-ctx-sqlite', 'e-chat-regex', 'e-cal-write-registry'], 'id': 'suite6-learning-loop', 'steps': ['hourly SQLite chat export', 'regex/heuristic extract', 'optional Bayesian keep/drop', 'append meta-learning-log / mutate rule-registry', 'nightly ECE calibration']}, {'evidence_ids': ['e-imp-cycle', 'e-adaptive-unimplemented'], 'id': 'suite6-improvement-audit', 'steps': ['observe metrics', 'compare GME patterns', 'micro-patch reasoning weights', 'validate via reasoning-metrics.md', 'append meta-audit']}]}
```

## Surface / Target Graph
- intelligence/_archived/workspace/setup-new-workspace.py | intelligence/_archived/workspace/setup-new-workspace.py | cli-archived
- intelligence/_archived/workspace/setup-new-workspace.md | intelligence/_archived/workspace/setup-new-workspace.md | doc-archived
- ops/scripts/process_context.sh | ops/scripts/process_context.sh | live-dangling
- intelligence/context-memory/graphiti_sink.py | intelligence/context-memory/graphiti_sink.py | live-unwired
- intelligence/_archived/learning/auto_calibrator.py | intelligence/_archived/learning/auto_calibrator.py | cli-archived
- intelligence/_archived/learning/feedback_collector.py | intelligence/_archived/learning/feedback_collector.py | cli-archived
- intelligence/_archived/learning/chat-learning-extractor.py | intelligence/_archived/learning/chat-learning-extractor.py | cli-archived
- intelligence/_archived/context-memory/context-extractor.py | intelligence/_archived/context-memory/context-extractor.py | cli-archived
- intelligence/_archived/improvement-loop.md | intelligence/_archived/improvement-loop.md | doc-archived

## Duplicate and Drift Register
- Workspace activation is SessionStart + setup_workspace_symlinks.sh; donor still documents Dropbox, .suite6-config.json, and a 22-file profile dump | AGENTS.md §2 + intelligence/workspace/SETUP_QUICK_START.md | Donor is migration evidence. Do not restore. Successor already live.
- Resume memory is Graphiti inject/PICKUP + sessionEnd S3 archive; donor extracts hourly SQLite composer blobs to JSON | ops/graphiti/hydration/archive_transcript.py + graphiti_memory_client.py | Hourly SQLite path is retired (RETIRED_export_chats_and_learning_processor.md). Meaningfulness-gate semantic may transfer; machinery must not.
- process_context.sh still calls intelligence/context-memory/context-extractor.py after that file was git-mv'd to _archived | retire process_context.sh with the tenx jobs, or retarget only after an authorized Graphiti owner exists | Live dangling wrapper. Close as cut-over residue, do not un-archive the extractor.
- CANONICAL_LAW §8 names graphiti_sink.py as durable-episode interface; CHANGELOG and no ops/graphiti callers say it was never wired | ops/graphiti/graphiti_memory_client.py (MCP) + hydration | Law/doc seam. Stronger observable owner is the Graphiti client. Do not revive sink as authority.
- intelligence/context-memory/README.md and INSTALLATION.md still tree-list the archived extractor as live | SETUP_QUICK_START.md deprecation stance + Graphiti hydrate docs | Beneficiary documentation drift from the 2026-07-19 archive.
- ops/feedback_loop_config.yaml points at .cursor-commands/ops/scripts/feedback_collector.py which never lived there | TODO.md B7; Graphiti write-on-correction (rule 87) | Dangling config. Do not copy archived collector into ops/scripts.
- adaptive-reasoning.md (live) still describes auto-tuning into meta-audit.md; improvement-loop.md (archived) is the paired unimplemented design | l9-structured-reasoning + make improve; adaptive-reasoning.md already stamps Not implemented | Keep the live 'not implemented' stamp. Do not restore improvement-loop.md as an owner.
- Two Readme-style surgical-edit texts: archived core-rules.md and learning/failures/learned-lessons-corpus.md | learned-lessons-corpus.md plus rules/70-tool-efficiency.mdc and 91-existing-code-source-of-truth.mdc | Corpus already holds the fragment. Archive copy is duplicate evidence.

## Nugget Register
- c-cutover-seam-closure | Finish Suite-6 pointer retirement on live seams | MERGE_WITH_EXISTING | leverage=5 | destination=TODO.md B7/B8/C3 plus CANONICAL_LAW.md §8, intelligence/context-memory/README.md, INSTALLATION.md, ops/scripts/process_context.sh, ops/feedback_loop_config.yaml
- c-implicit-outcome-label | Label decision outcomes from unambiguous post-decision behavior | PORT_WITH_HARDENING | leverage=4 | destination=Graphiti write-on-correction (rules/87, l9-graphiti-memory) plus optional session_debt; never foundation rule-registry
- c-resume-episode-threshold | Resume-context episodes require a declared signal threshold | PORT_WITH_HARDENING | leverage=3 | destination=ops/graphiti/hydration SessionHydrationPacket / inject — not archive_transcript S3 policy
- c-observe-compare-patch-validate | Scheduled observe-compare-patch-validate improvement cycle | MERGE_WITH_EXISTING | leverage=2 | destination=make improve, kernels/Recursive Alignment.md, kernels/Validate & Repair.md, L4 receipts
- c-surgical-edits-only | Surgical edits over whole-file rewrite | MERGE_WITH_EXISTING | leverage=2 | destination=learning/failures/learned-lessons-corpus.md + rules/70-tool-efficiency.mdc + 91-existing-code-source-of-truth.mdc
- c-immutable-self-mod-audit | Immutable record of self-modifications and rollbacks | MERGE_WITH_EXISTING | leverage=2 | destination=Graphiti PICKUP / L4 receipts / git history

## Beneficiary Fit
- c-cutover-seam-closure | MERGE_WITH_EXISTING | TODO.md B7/B8/C3 plus CANONICAL_LAW.md §8, intelligence/context-memory/README.md, INSTALLATION.md, ops/scripts/process_context.sh, ops/feedback_loop_config.yaml
- c-implicit-outcome-label | PORT_WITH_HARDENING | Graphiti write-on-correction (rules/87, l9-graphiti-memory) plus optional session_debt; never foundation rule-registry
- c-resume-episode-threshold | PORT_WITH_HARDENING | ops/graphiti/hydration SessionHydrationPacket / inject — not archive_transcript S3 policy
- c-observe-compare-patch-validate | MERGE_WITH_EXISTING | make improve, kernels/Recursive Alignment.md, kernels/Validate & Repair.md, L4 receipts
- c-surgical-edits-only | MERGE_WITH_EXISTING | learning/failures/learned-lessons-corpus.md + rules/70-tool-efficiency.mdc + 91-existing-code-source-of-truth.mdc
- c-immutable-self-mod-audit | MERGE_WITH_EXISTING | Graphiti PICKUP / L4 receipts / git history

## Safety and Portability Audit
- CONFIRMED | Donor Python was inventoried and read, not executed.
- CONFIRMED | No beneficiary implementation, wiring, commit, or push was performed by this harvest.
- CONFIRMED | Dropbox paths, LaunchAgents, .suite6-config.json, n8n kit, rule-registry writes, and ECE gates were not treated as transferable machinery.
- CONFIRMED | S3 transcript-archive completeness was preserved as stronger beneficiary policy versus donor hourly JSON snapshots.
- INFERENCE | No secret values were observed in the nine archive files; machine home paths in setup-new-workspace.md were treated as forbidden path evidence, not copied.

## Concept Acceptance Tests
- c-cutover-seam-closure | Given a live pointer to intelligence/context-memory/context-extractor.py or ops/scripts/feedback_collector.py | When cut-over closure is applied | Then the pointer is retired or retargeted to Graphiti client / SessionStart, and the archived file stays archived | Must not restore the archived extractor, collector, or setup script into a live path
- c-implicit-outcome-label | Given a warn/block decision and a later unambiguous user action that the mapping classifies | When outcome labeling runs | Then a Graphiti outcome/lesson episode is written with agent_id and evidence, and no threshold or temperature file changes | Must not write foundation/logic/rule-registry.json or copy feedback_collector.py into ops/scripts
- c-resume-episode-threshold | Given a derived resume packet with no actions, files, decisions, or completion signals | When hydration/inject considers writing that packet as a session episode | Then the packet is omitted or marked low-signal, while closed-chat S3 archive is unchanged | Must not import foundation/_archived/logic/probabilistic_engine.py or reinstall hourly SQLite extraction
- c-observe-compare-patch-validate | Given a finished local contract | When improvement is recorded | Then kernels run and a receipt exists without writing intelligence/meta-audit.md | Must not stand up ops/reasoning-metrics.md from this archive
- c-surgical-edits-only | Given an existing file edit | When an agent changes it | Then the change is targeted and formatting is preserved | Must not reintroduce intelligence/_archived/core-rules.md as a live rule file
- c-immutable-self-mod-audit | Given a self-modification or kernel pass | When the session closes or L4 records | Then the event is in Graphiti or an L4 receipt, not a Suite-6 json mirror | Must not recreate intelligence/meta-audit.md as a live owner
- c-suite6-workspace-machinery | Given this harvest | When workspace enablement is considered | Then SETUP_QUICK_START + SessionStart remain the owners | Must not execute or copy setup-new-workspace.py or write .suite6-config.json
- c-mandatory-session-dump | Given a new session | When activation runs | Then SessionStart additional_context is the load surface | Must not require reading the archived 22-file list
- c-ece-registry-autocalibrate | Given this harvest | When calibration transfer is considered | Then the concept is rejected | Must not schedule auto_calibrator.py or revive rule-registry.json writes
- c-regex-chat-to-fol | Given a chat that matches 'should automatically extract' | When learning is recorded | Then Graphiti lesson write or harvest qualification is used | Must not run chat-learning-extractor.py or emit canned FOL as a live rule
- c-hourly-sqlite-extract | Given a closed Cursor chat | When words must be preserved | Then sessionEnd archive_transcript writes S3 json, not an hourly vscdb copy | Must not reinstall com.tenx.chat-export or treat composer.composerData as resume SSOT

## Rejected and Local Concepts
- c-suite6-workspace-machinery | REJECT | Dropbox + .suite6-config.json + n8n kit workspace enablement
- c-mandatory-session-dump | REJECT | Read 22+ profiles and all learning files at every session start
- c-ece-registry-autocalibrate | REJECT | Nightly ECE temperature and threshold auto-write
- c-regex-chat-to-fol | REJECT | Regex chat phrases into FOL governance rules
- c-hourly-sqlite-extract | MIGRATION_CONTEXT | Hourly workspaceStorage SQLite composer extraction

## Highest-Leverage Next Action
c-cutover-seam-closure

## UNKNOWNs
- Whether any machine still has com.tenx.chat-export, com.tenx.learning-processor, or com.cursor.context.processor loaded.
- Whether graphiti_sink.emit_session was ever invoked outside this repo (learning/graphiti-episodes/manifest.json still names it).
- Whether implicit feedback_collector events were ever produced in production telemetry (telemetry/_archived only).
- Whether CANONICAL_LAW §8 graphiti_sink row is intentional leftover documentation or an unapplied law edit.
- Exact remaining LaunchAgent plist contents on this host were not inspected in this harvest.
