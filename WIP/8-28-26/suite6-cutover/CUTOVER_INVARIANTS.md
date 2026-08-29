# Suite-6 archive cut-over invariants

**plan_id:** `plan.intelligence.suite6_archive_cutover.v1`  
**harvest SSOT:** `WIP/8-28-26/intelligence-harvest/archived-suite6/harvest.json` (receipt PASS)  
**donor:** `intelligence/_archived/` — evidence, never authority. Do not import or execute.

Bound at freeze (todo-01):

- HEAD: `7d13b66ec881e82ede5c092ceb28e7eb659536d9`
- LaunchAgents (`tenx` / `context.processor`): **absent** — U1 accept_bounded: fully retire wrappers (no loaded-job delay)
- Overlap: harvest WIP allowed; do not scoop foreign plan moves or `Makefile`

---

## Outcome map (six pairs only)

Any other `(action, feedback)` pair is a **no-op**. Require an existing Graphiti **decision episode id**. Stamp `agent_id`. Write `--kind lesson` via `graphiti_memory_client`. Do not port `_parse_feedback` text heuristics. Do not write a registry or threshold file.

| action | feedback | label |
|---|---|---|
| `WARN_AND_LOG` | `edited_file` | `CORRECT` |
| `WARN_AND_LOG` | `said_fine` | `TOO_STRICT` |
| `BLOCK_OR_REQUIRE_REVIEW` | `added_header` | `CORRECT` |
| `BLOCK_OR_REQUIRE_REVIEW` | `overrode` | `TOO_STRICT` |
| `LOG_ONLY` | `error_occurred` | `TOO_LENIENT` |
| `LOG_ONLY` | `no_issues` | `CORRECT` |

---

## Resume signals (declared weights)

Incidental numbers, not a Bayesian engine. Apply only to **optional derived Graphiti episode writes** in `ops/graphiti/hydration/close_session.py` / inject. Named constants live in `ops/graphiti/hydration/promotion_rules.yaml`. Do not create a second confidence SSOT. Do not revive `probabilistic_engine.py`.

| signal | score | weight |
|---|---|---|
| actions | `min(n/3, 1)` | 0.25 |
| files | `min(n/5, 1)` | 0.20 |
| decisions | `min(n/2, 1)` | 0.20 |
| message volume | `min(n/10, 1)` | 0.15 |
| code present | `1` or `0` | 0.10 |
| completion | `1` or `0.3` | 0.10 |

---

## Fail-open

- Scorer exception → **write** (keep). Never drop because the scorer crashed.
- `compile_session_packet.py` **always** emits `SessionHydrationPacket`. Low-signal optional episode may drop; the packet must not.

---

## S3 all-words

`ops/graphiti/hydration/archive_transcript.py` writes the closed-chat document for every session, including low-signal. Do not filter transcripts. Policy: `ops/scripts/RETIRED_export_chats_and_learning_processor.md`.

---

## Wrapper-must-resolve

Live wrappers must not exec missing archive Python and must not point at `_archived/` or at the new scorer.

| wrapper | after Wave 1 |
|---|---|
| `ops/scripts/process_context.sh` | retired stub (exit 0); does not exec `context-extractor.py` |
| `ops/scripts/show_context.sh` | retired stub; does not read sqlite/session JSON as SSOT |
| `ops/scripts/session_init.sh` | retired stub; SessionStart hook is the only activation |
| `ops/feedback_loop_config.yaml` | no `feedback_collector.script` |
| `intelligence/context-memory/graphiti_sink.py` | deleted (never wired) |

---

## Delete-gate `rg`

Run from repo root **before** `git rm -r intelligence/_archived`. No-go if any live caller remains under `ops/`, `intelligence/` (except `_archived`), or `skills/`. Historical hits in `CHANGELOG.md`, `TODO.md`, and `intelligence/workspace/SETUP_QUICK_START.md` are allowed.

```bash
rg -n --glob '!intelligence/_archived/**' --glob '!.git/**' \
  -e 'context-extractor\.py' \
  -e 'feedback_collector\.py' \
  -e 'auto_calibrator\.py' \
  -e 'setup-new-workspace\.py' \
  -e 'setup-new-workspace\.md' \
  -e 'chat-learning-extractor\.py' \
  -e 'improvement-loop\.md' \
  -e 'meta-audit\.md' \
  -e 'core-rules\.md' \
  -e 'graphiti_sink\.py' \
  ops intelligence skills
```

Allowed leftover mentions: `CHANGELOG.md`, `TODO.md` (historical / ABSENT row), `intelligence/workspace/SETUP_QUICK_START.md` (do-not-follow pointer).

---

## Already owned (no new features)

- `make improve` = observe-compare-patch
- Graphiti / L4 receipts = audit log
- lessons corpus + rules 70 / 91 = surgical edits
- wrapper-must-resolve = Wave 1 proof (this packet)
