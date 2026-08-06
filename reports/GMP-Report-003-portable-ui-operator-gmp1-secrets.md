# GMP Report 003 — Portable UI Operator GMP-1 (Secrets foundation) + ops relocate

**Run ID:** GMP-003-portable-ui-operator-gmp1
**Date:** 2026-08-06
**Target Branch:** main (local working tree; no commit/push)
**Scope:** Relocate `operations/ops` → `ops/`; M0+M1 secrets registry/resolver + `l9-aws-secrets` + `ui-operator` pyproject extra (additive)
**Commit Message:** `(not committed — user did not request commit)`

## 1. PLAN

**Context:** Execute relocate plan then Portable UI Operator GMP-1 (M0+M1) via `l9-gmp-protocol`.

**Pre-Validation**
| Check | Evidence | Status |
|---|---|---|
| P0 write root `ops/secrets`, `skills/` | Bound; nested `operations/ops` relocated first | PASS |
| P1 igorbot CSV enabled IDs | Synced via `gh` API (private repo); 19 enabled incl. overlays | PASS |
| P2 AWS identity + resolve `--check` | `aws sts` OK; `OK ref=openclaw-igorbot/github#token` (no value printed) | PASS |

**MEMORY_PREFETCH:** Graphiti conflicts consulted (`cursor-governance` group); prior facts on GMP reports / package access — no blocking conflict for secrets mirror.

**CODE_GRAPH_BASELINE:** SKIPPED (no PlasticOS GRAPH REQUIRED paths).

**MODIFICATION LOCK — may-modify**
- `operations/ops/operational-oversight.md` → `ops/operational-oversight.md` (git mv)
- `README.md` (drop stale `operations/` listing)
- `ops/secrets/**` (new)
- `skills/l9-aws-secrets/**` (new)
- `skills/AUTONOMY_MANIFEST.yaml`
- `pyproject.toml` (append `ui-operator` extra; append `.claude` to norecursedirs)
- `requirements.txt` (pointer comment)
- `uv.lock` / `environment/claude-code/generated/skill-registry.json` (regenerable)

**must-not-modify**
- igorbot inventory SSOT; Keychain/cookie paths; `ops/ui-operator/` (GMP-2); root AGENTS/CANONICAL_LAW appends (GMP-3); secret values

**ADRs CONSULTED:** AGENTS.md § toolchain/protected pyproject; Portable UI Operator plan; igorbot resolver protocol.

| ID | File | Operation | Status |
|---|---|---|---|
| T-REL | `ops/operational-oversight.md` | Create via git mv | APPLIED |
| T-001 | `ops/secrets/sync_igorbot_manifest.py` | Create | APPLIED |
| T-002 | `ops/secrets/resolve_secret.py` | Create | APPLIED |
| T-003 | `ops/secrets/openclaw-igorbot.registry.yaml` + schema/overlays | Create | APPLIED |
| T-004 | `skills/l9-aws-secrets/` + AUTONOMY_MANIFEST wire | Create/Insert | APPLIED |
| T-005 | `pyproject.toml` ui-operator + `requirements.txt` pointer | Insert | APPLIED |
| T-006 | `ops/secrets/test_aws_secrets.py` | Create | APPLIED |

## 2. CHANGES

- Relocated oversight doc; removed empty `operations/`
- New secrets runtime under `ops/secrets/` (sync via `gh` for private CSV, resolve `--check`/`--ref`, overlays for `ui-session-*` with `provisioned: false`)
- Skill `l9-aws-secrets` wired (auto_invoke + claude_routing)
- Optional-deps `ui-operator = [playwright==1.56.0, boto3>=1.34,<2]`
- Unit tests mocked AWS; live `--check` OK without echoing values

## 3. TODO → CHANGE MAP

| TODO | Phase | Result |
|---|---|---|
| Relocate operations/ops | pre | VERIFIED — `R operations/ops/... -> ops/operational-oversight.md` |
| M0 registry + sync | 2 | VERIFIED — 26 secrets / 19 enabled |
| M0 resolve | 2 | VERIFIED — live check OK |
| M1 skill wire | 2 | VERIFIED — skill-registry + AUTONOMY_MANIFEST |
| M1 pyproject extra | 2 | VERIFIED — append-only |
| Tests | 3 | VERIFIED — 6 passed |
| make pr | 4 | VERIFIED — PASS |

## 4. VALIDATION

| Gate | Result |
|---|---|
| `py_compile` sync/resolve | PASS |
| `pytest ops/secrets/test_aws_secrets.py` | 6 passed |
| `resolve_secret --ref openclaw-igorbot/github#token --check` | `OK ref=...` exit 0 |
| `ruff check` on new Python | PASS |
| `make pr` | PASS — local PR gate clean (changed files only) |
| Secret values in git/registry | None (refs only) |

## 5. INVARIANTS CHECK

- No Keychain / Chrome Safe Storage usage
- No secret values committed
- `pyproject.toml` existing keys preserved; `ui-operator` added
- Playwright not on `dev` extra
- Protected paths untouched beyond declared lock
- Removed local untracked `tests/ops/` mirror that duplicated `ops/` (collection poison); test co-located at `ops/secrets/test_aws_secrets.py`

## 6. DECLARATION

Phases 0-6 complete. No assumptions. No drift.

GMP run GMP-003-portable-ui-operator-gmp1 finalized.
No further changes permitted.

## 7. GRAPHITI MEMORY EVIDENCE

- Phase 0: `graphiti_memory_client.py conflicts` OK; MEMORY_PREFETCH cited prior GMP/package-access facts
- No new episode write required for this run (local evidence report only)

## Next (out of this run)

GMP-2: `ops/ui-operator` console + operating playbook + GitHub cartridge + `l9-ui-operator`.

## Amendment 2026-08-06 — SSOT inversion

Inventory authority moved to Cursor-Governance. `sync_secrets_registry.py` lists AWS Secrets Manager under `openclaw-igorbot/` and updates the local registry. No fetch from Quantum-L9/igorbot. Consumers depend on this repo.
