---
name: C5 C6 harvest land
overview: Do not move the SSOT clone. It already lives at `$HOME/.cursor-governance`. Fix the leftover Dropbox LaunchAgent (report-only in the checker; one-time host removal), extend `--machine` wiring coverage, and port corpus reachability as an advisory `ops/scripts` report. Do not restore the archived Suite-6 validator file.
todos:
  - id: host-plist
    content: "One-time: confirm LaunchAgent unloaded; move ~/Library/LaunchAgents/com.cursor.governance-monitor.plist aside. Do not delete Dropbox. Do not unload from the checker."
    status: completed
  - id: machine-scan
    content: Extend check_governance_wiring.sh --machine to FAIL on installed plists that reference Dropbox/CloudStorage or a non-SSOT governance root; warn if LaunchAgents dir missing; never mutate. Add fixture tests.
    status: completed
  - id: reachability
    content: Add ops/scripts/audit_corpus_reachability.py with a declared entrypoint set, name-based reachability, advisory JSON under reports/, Makefile corpus-reachability + pr-full-corpus append, and C5 acceptance tests.
    status: completed
isProject: false
kernel_pass:
  bound_path: c5_c6_harvest_land_3bd25547.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-08-28T23:20:00Z
    body_sha256: "e99c9ab70c56e43a67b2a3cce7f4d4885540912328c4a5b01b92c84b5ef2e9c0"
    deltas:
      - "Landed report-only scan_launchagents.py so the wiring checker never unloads agents"
      - "Corpus audit skips generic basenames so SKILL.md is name-reachable, not a substring hit"
      - "Host leftover Dropbox agents moved to LaunchAgents/_retired; Dropbox tree left in place"
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-08-28T23:21:00Z
    body_sha256: "e99c9ab70c56e43a67b2a3cce7f4d4885540912328c4a5b01b92c84b5ef2e9c0"
    deltas:
      - "Advisory reachability always exits 0 with delete_authorization false"
      - "Makefile append-only corpus-reachability plus pr-full-corpus; make pr unchanged"
      - "Fake-HOME LaunchAgent fixtures and C5 pytest; --machine PASS after plist move"
---

# Land C5 reachability and C6 machine-plane path law

## Answer: do not move the SSOT clone

The live SSOT is already the GitHub clone at `$HOME/.cursor-governance`. [`ops/scripts/resolve_governance_paths.sh`](ops/scripts/resolve_governance_paths.sh) does not consult Dropbox. The Dropbox path is leftover Suite-6 residue: an installed-but-unloaded LaunchAgent whose wrapper still has a three-branch resolver with a Dropbox fallback.

You do **not** relocate the clone. You remove the leftover agent from this machine and make the machine-plane checker able to see the next one.

## What “activate the validator” means here

Do **not** restore [`execution-governance/_archived/validation/governance-validator.py`](execution-governance/_archived/validation/governance-validator.py). Its workspace assertions (`.cursorrules`, `.l9_governance-config.json` `suite_version 6.0.0`) are retired Suite-6 contract surface; live [`ops/scripts/check_governance_wiring.sh`](ops/scripts/check_governance_wiring.sh) is already a strict superset for wiring.

The checks the live gates still lack are exactly the two nuggets:

- C5 — computed corpus reachability (no live owner)
- C6 — machine-local LaunchAgents that resolve a governance root (path lint cannot see them)

## C6 — leftover agent + checker coverage

Two layers, kept distinct so the checker never mutates the host.

**Host hygiene (this machine, one-time, authorized by this request):**

- `launchctl list` — confirm still unloaded
- Do **not** `launchctl unload` from the checker
- Move (do not silently delete) `~/Library/LaunchAgents/com.cursor.governance-monitor.plist` aside, e.g. `~/Library/LaunchAgents/_retired/`, so a later `launchctl load` cannot re-arm it
- Leave the Dropbox tree itself alone; it is not the SSOT and is not in this repo

**Repo: extend `--machine` in [`ops/scripts/check_governance_wiring.sh`](ops/scripts/check_governance_wiring.sh)** after the existing sessionEnd/Graphiti block (around line 315), as a new subsection that:

- If `$HOME/Library/LaunchAgents` is missing: `warn` and continue (CI / Linux)
- Else scan `*.plist` for ProgramArguments, StandardOutPath, StandardErrorPath, and WorkingDirectory
- **FAIL** if any installed plist (loaded or not) references Dropbox, `Library/CloudStorage`, or a governance root other than `$HOME/.cursor-governance`
- Report label + target path; never `bootout` / unload / delete from the script
- Cover C6 acceptance tests from [`WIP/8-28-26/execution-governance-harvest/harvest.json`](WIP/8-28-26/execution-governance-harvest/harvest.json)

Tests: add [`ops/scripts/tests/test_launchagent_scan.sh`](ops/scripts/tests/test_launchagent_scan.sh) with a fake `HOME`/`Library/LaunchAgents` fixture (forbidden Dropbox plist → FAIL; missing dir → warn/PASS; SSOT-only path → PASS). Do not extend `test_workspace_kind.sh`. Do not touch the real LaunchAgents directory from tests.

### Kernel-locked write_allow

- `ops/scripts/check_governance_wiring.sh` (`--machine` LaunchAgent scan only)
- `ops/scripts/tests/test_launchagent_scan.sh` (new)
- `ops/scripts/audit_corpus_reachability.py` (new)
- `tests/ops/scripts/test_audit_corpus_reachability.py` (new)
- `reports/corpus-reachability.json` (generated advisory)
- `Makefile` append-only: `corpus-reachability` target and `pr-full-corpus` hook

Host plist move is machine-local and is not a repo path.

[`ops/scripts/run_pr_gate.sh`](ops/scripts/run_pr_gate.sh) already runs `--machine` on local Cursor hosts, so this machine cannot `make pr` until the leftover plist is moved. Host hygiene (`host-plist`) is already completed. Land the checker (`machine-scan`) next, then C5 reachability.

## C5 — corpus utilization as computed reachability

New script [`ops/scripts/audit_corpus_reachability.py`](ops/scripts/audit_corpus_reachability.py). Advisory: exit 0, write `reports/corpus-reachability.json` (and a short markdown sibling if the renderer stays tiny). Unreachable does **not** authorize delete.

**Declared entrypoint set** (named in the report, not inferred):

- [`skills/AUTONOMY_MANIFEST.yaml`](skills/AUTONOMY_MANIFEST.yaml)
- [`commands/COMMANDS_MANIFEST.yaml`](commands/COMMANDS_MANIFEST.yaml)
- [`rules/RULES-MANIFEST.yaml`](rules/RULES-MANIFEST.yaml)
- [`ops/generated/skill-registry.json`](ops/generated/skill-registry.json)
- [`.pre-commit-config.yaml`](.pre-commit-config.yaml)
- Makefile recipes (script paths and target names)
- [`ops/hooks/hooks.json.template`](ops/hooks/hooks.json.template)
- Claude adapter plugin/settings: [`environment/agents/adapters/claude-code/plugins.desired.json`](environment/agents/adapters/claude-code/plugins.desired.json) and [`environment/agents/adapters/claude-code/settings.template.json`](environment/agents/adapters/claude-code/settings.template.json)

**Population:** tracked files under `skills/`, `commands/`, `rules/`, `ops/scripts/`, `ops/hooks/`, `environment/agents/`, `workflows/` — skip `_archived/`, `WIP/`, generated trees, `__pycache__`.

**Reachable if any of:**

- path or basename appears in an entrypoint artifact
- registered by name (skill / command / rule id) — so a skill with a `SKILL.md` is not an orphan just because nothing imports it
- imported by a reachable Python module (one hop from entrypoint scripts)

Report: counts per category, utilization ratio, unreachable paths, and the entrypoint set used. First land will list `execution-governance/_archived/**` as unreachable — that is evidence, not a fail.

Wire **append-only** into [`Makefile`](Makefile) `pr-full-corpus` (nightly / `make pr-full`), not `make pr`. Add `make corpus-reachability` as the direct target.

Tests: `tests/ops/scripts/test_audit_corpus_reachability.py` covering the three C5 acceptance tests (doc-only file → unreachable with entrypoints named; name-loaded skill/rule → reachable; report is not a delete gate / exit 0 with orphans present).

## Out of scope

- Relocating `$HOME/.cursor-governance`
- Deleting the Dropbox folder
- Restoring or rewiring `governance-validator.py`
- Auto-delete of unreachable files
- C1 time-series compliance, C3 rule-coverage inversion (not requested)

## Validation

- Fake-HOME LaunchAgent fixtures
- Reachability unit tests
- `make corpus-reachability` on this checkout (advisory JSON)
- After plist move: `bash ops/scripts/check_governance_wiring.sh --machine "$(pwd)"` PASS
- `make precommit-repo` on changed files only
