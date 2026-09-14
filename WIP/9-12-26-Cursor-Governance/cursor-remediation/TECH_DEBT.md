# Cursor remediation — tech-debt ledger

Human twin of [`tech_debt.json`](tech_debt.json). Ranked by impact, then
frequency. Every row traces to an observed finding in one of the two
environment-experience packs or to evidence resolved in the 2026-09-02
session. No invented findings; no secret values; no archives in this folder.

**Sources (read in place):**

- **Session pack** — `/tmp/l9-env-exp-pack-20260902/`
  (`cursor-2026-09-02-pr-remediator`; ids `FAIL-01…11`, `FRIC-01…06`, `IMP-01…09`).
- **Other agent's pack** — `reports/environment_experience_improvement_pack.zip`
  (binding head `119d0df0`; ids `F-01…05`, `FR-01…10`, `IMP-BOOT/LOADER/ENV-*`).
  Absent at planning time, **present at build time** — ingested, so the planned
  UNKNOWN rows were replaced with real ones (unknown register U-A: resolved).
- **Resolved-in-chat** — hydrate DEGRADED attributed to the bootstrap
  `*degraded*` glob (not the compiler); `~/.cursor/graphiti.env` predates the
  tracked init script (birth 2026-06-07 vs script 2026-07-04; never
  overwrites); the Claude `$HOME` receipt was written 2026-09-02T20:19:36Z by
  Claude `install.sh` via a `$HOME`-workspace run, not by Cursor's hook.

## Fixed by this build (branch `feat/cursor-adapter-remediation`)

| id | impact | owner | finding | fixed by |
|---|---|---|---|---|
| TD-01 | high | bootstrap | Hydrate reported DEGRADED while the packet said `degraded: false` (`FAIL-01`, `IMP-01`) | `ops/scripts/classify_hydrate_state.py` + bootstrap wiring; packet booleans are the only positives |
| TD-02 | high | bootstrap | Receipts had no surface/workspace identity; a Claude `$HOME` receipt read as session state (`FAIL-02`, `F-01`, `F-04`, `IMP-02`, `IMP-BOOT-01`) | surface-parameterized reader; `stale_other_surface` downgrade; `cursor-adapter` report row |
| TD-03 | high | bootstrap | Shared bootstrap accepted `--workspace $HOME` (`IMP-07`, `F-01`) | `$HOME` refusal in `bootstrap_agent_environment.sh` and `adapters/cursor/install.sh` |
| TD-04 | high | env | Agent shells missed Homebrew PATH / bound the wrong python (`FRIC-01`, `FAIL-09`, `IMP-05`, `FR-01`) | SessionStart PATH prepend; locked-venv documentation in the Cursor adapter README |
| TD-05 | high | adapter | `memory_prefetch.py` injected `agent_id=claude-code` hydrate blocks into Cursor sessions (resolved-in-chat, `FR-04`) | runtime-marker guard mirroring `session_start_claude_governance.sh:89-92` |

## Open (ranked)

| id | impact | owner | finding | done condition |
|---|---|---|---|---|
| TD-06 | med | loader | Bash loader overwrites, Python loader setdefaults (`FAIL-03`, `FR-02`, `IMP-03`, `IMP-LOADER-01`) | one documented precedence matrix + a test both callers satisfy |
| TD-07 | med | env | Token home is `~/.cursor/graphiti.env`, docs point at overlay; `env_status` misnames it (`FAIL-04`, `IMP-04`) | **human secret-plane decision** — env_status names the source class, no values |
| TD-08 | med | adapter | `make claude-env` applies Claude-cloud account scoring to Cursor shells (`F-02`, `F-03`, `IMP-BOOT-03`) | no Claude marker ⇒ `NOT_APPLICABLE` exit 0 |
| TD-09 | med | bootstrap | Readiness receipt READY while bootstrap receipt DEGRADED, same stamp (`F-04`, `IMP-BOOT-04`) | readiness folds in shared_bootstrap state |
| TD-10 | med | bootstrap | Projection mounts `~/.cursor-governance.bak.*` clones (`FR-06`, `IMP-BOOT-02`) | receipt shows no bak mount roots |
| TD-11 | med | env | Stale `l9-governance.backup.20260814_232353` plugin on the always-apply path (`FR-05`, `IMP-ENV-02`) — still visible in this session | new sessions apply no backup-path rules |
| TD-12 | low | env | `graphiti.env.defaults` names the retired HTTP side door (`FR-03`, `IMP-ENV-01`) | no `L9_MEMORY_HTTP_URL` matches |
| TD-13 | low | env | gitleaks pin warning folded beside real degrades (`FAIL-10`, `FR-09`) | `gitleaks_pin=warn` separated in the receipt |
| TD-14 | low | loader | Archived `env_loader.py` rediscoverable without its CSV (`F-05`, `IMP-LOADER-04`) | raises retired, or deleted per TODO.md A3 |
| TD-15 | low | env | GitHub protection API shape undocumented — only full-document PUT works (`FAIL-06`, `IMP-06`) | ops note + full-PUT helper; DELETE gate unweakened |
| TD-16 | low | bootstrap | `governance_refresh` receipt reads `never_ran` (`FAIL-11`) | fresh state after SessionStart |
| TD-17 | low | bootstrap | PICKUP surfaced a finished objective as `next=` (`FAIL-07`) | newest session-scoped episode wins |
| TD-18 | low | env | zsh agent-shell discipline undocumented (`FAIL-05`, `FRIC-05`) | quoting/setopt note; scripts shellcheck-clean for both patterns |
| TD-19 | low | env | Env-experience packs duplicated under two WIP trees (`FRIC-06`) | wip-hygiene dedupe or `landed:` inventory |

## Unknown register

- **U-A — resolved.** Other agent's zip existed at build time at both claimed
  paths and was ingested; no invented ids were needed.
- **U-B — open.** Parent process of the 20:19:36Z Claude repair (sibling
  Claude window vs harness): receipt facts recorded; parent unknowable from disk.
- **U-C — open.** Writer of `~/.cursor/graphiti.env` (2026-06-07): predates
  the tracked init script; bytes untouched; provenance unknown.
