# L9_META:
#   repo: Quantum-L9/L9-Graphite-Memory
#   layer: docs/adr
#   owner: platform
#   status: accepted
#   created: 2026-07-05

# ADR-001: Infisical Universal Auth for Secrets Management

**Status:** Accepted  
**Date:** 2026-07-05  
**Deciders:** Quantum-L9 Platform Team  
**Supersedes:** macOS Keychain + flat `.env` file pattern (`graphiti_env_loader.py`)

---

## Context

L9-Graphite-Memory requires runtime access to sensitive credentials (Zep Cloud API keys, OpenAI API keys, MCP tokens) across multiple deployment contexts:

1. **Local development** — developer machines running Cursor, Claude Desktop, or other MCP-aware IDEs.
2. **CI/CD pipelines** — GitHub Actions running integration tests.
3. **Long-running MCP servers** — persistent processes serving memory queries to multiple agents.
4. **Multi-agent environments** — any agent framework (LangChain, CrewAI, AutoGen, Manus) that speaks MCP.

The previous approach used a 3-tier loading hierarchy:
- `config/graphiti.env.defaults` (committed safe defaults)
- `~/.cursor/graphiti.env` (machine-level overrides)
- macOS Keychain via `security find-generic-password` (actual secrets)

This approach failed because:
- **Platform-locked:** macOS Keychain is unavailable on Linux, Windows, CI runners, and containers.
- **Agent-hostile:** Each new agent or machine required manual Keychain provisioning.
- **No rotation:** Secrets were static; rotation required manual intervention on every machine.
- **No audit trail:** No visibility into which machine accessed which secret and when.
- **Scattered state:** Secrets lived in N different places across N machines with no single source of truth.

---

## Decision

Replace the deprecated `graphiti_env_loader.py` with a centralized secrets adapter (`secrets.py`) that uses **Infisical Universal Auth** via the `infisical-python` SDK (v2.3.6).

The adapter follows the exact contract established by `@quantum-l9/infisical-config` (TypeScript reference implementation in `Quantum-L9/infisical-config`), ported to Python.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  INFISICAL VAULT (cloud.infisical.com or self-hosted)           │
│    └─ Project: quantum-l9                                       │
│         └─ Environment: prod | staging | dev                    │
│              └─ Path: / (or /graphiti, /zep, etc.)              │
│                   └─ Secrets: ZEP_API_KEY, OPENAI_API_KEY, ...  │
│                                                                 │
│  MACHINE IDENTITY (Universal Auth)                              │
│    └─ Client ID + Client Secret → short-lived access token      │
│    └─ One identity per deployment context                       │
│                                                                 │
│  RUNTIME FLOW:                                                  │
│    1. Process starts with 3 bootstrap env vars                  │
│    2. secrets.load_secrets_sync() authenticates to Infisical    │
│    3. Fetches all secrets for environment/path                  │
│    4. Injects into os.environ (non-destructive by default)      │
│    5. Downstream code reads os.environ["ZEP_API_KEY"] normally  │
│                                                                 │
│  ROTATION FLOW:                                                 │
│    A. SIGHUP handler → refresh_secrets(overwrite=True)          │
│    B. Interval timer → refresh every 900s (belt-and-suspenders) │
│    C. Infisical dual-phase rotation → old credential valid      │
│       during overlap window → all instances refresh before      │
│       old credential revoked                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Bootstrap Contract

Every deployment context needs exactly **3 environment variables** to boot:

| Variable | Description | Source |
|----------|-------------|--------|
| `INFISICAL_CLIENT_ID` | Machine identity client ID | Infisical dashboard |
| `INFISICAL_CLIENT_SECRET` | Machine identity client secret | Infisical dashboard |
| `INFISICAL_PROJECT_ID` | Project containing the secrets | Infisical dashboard |

Optional overrides:

| Variable | Default | Description |
|----------|---------|-------------|
| `INFISICAL_ENV` | `prod` | Environment slug |
| `INFISICAL_SECRET_PATH` | `/` | Secret folder path |
| `INFISICAL_SITE_URL` | (Infisical Cloud) | Self-hosted URL |
| `INFISICAL_RECURSIVE` | `0` | Pull nested folders |
| `INFISICAL_REQUIRED` | `0` | Abort on failure |

---

## Fail-Soft Behavior

| Condition | Behavior |
|-----------|----------|
| All 3 bootstrap vars missing | No-op. Log debug. Return `{loaded: false, source: "environ"}` |
| Partial config (1 or 2 vars set) | Log warning. Return `{loaded: false, source: "environ"}` |
| `infisical-python` not installed | Log warning. Return `{loaded: false, source: "environ"}` |
| Infisical API unreachable | Log warning. Return `{loaded: false, source: "environ"}` |
| Any of above + `INFISICAL_REQUIRED=1` | **Raise RuntimeError** — hard fail, process aborts |

This ensures:
- Local dev without Infisical still works (reads whatever is in `os.environ`).
- CI without Infisical secrets still runs non-integration tests.
- Production with `INFISICAL_REQUIRED=1` fails fast if vault is unreachable.

---

## Rotation Strategy

For long-running MCP server processes:

1. **SIGHUP handler** — `install_sighup_reload()` registers a signal handler that calls `refresh_secrets(overwrite=True)` on SIGHUP. External rotation orchestrators (systemd, Kubernetes) send SIGHUP after rotating.

2. **Interval refresh** — `start_refresh_interval(900)` creates an asyncio task that re-fetches every 15 minutes. Belt-and-suspenders: catches rotation even without explicit signal.

3. **Infisical dual-phase rotation** — Infisical keeps the old credential valid during an overlap window. As long as `interval_seconds < overlap_window`, all instances will refresh before the old credential is revoked.

---

## Consequences

### Positive

- **Platform-agnostic:** Works on macOS, Linux, Windows, containers, CI runners.
- **Agent-universal:** Any agent that starts the MCP server gets secrets automatically.
- **Single source of truth:** All secrets in one vault with audit trail.
- **Zero committed secrets:** Only 3 bootstrap vars needed (can be injected by CI, systemd, Docker, etc.).
- **Rotation-ready:** SIGHUP + interval refresh handles credential rotation without restarts.
- **Contract-aligned:** Mirrors the TypeScript `@quantum-l9/infisical-config` exactly.

### Negative

- **New dependency:** `infisical-python` SDK added to `pyproject.toml`.
- **Network dependency at boot:** First `load_secrets_sync()` call requires Infisical reachability (mitigated by fail-soft).
- **Infisical vendor coupling:** If Infisical goes down or changes API, secrets loading fails (mitigated by fail-soft + `os.environ` fallback).

### Neutral

- **No breaking change to downstream code:** All modules still read `os.environ["ZEP_API_KEY"]` etc. They don't know or care where the value came from.
- **Backward compatible:** If someone still has a local `.env` file or exports vars manually, those are respected (non-destructive injection).

---

## Alternatives Considered

| Alternative | Reason Rejected |
|-------------|-----------------|
| macOS Keychain (previous) | Platform-locked, no rotation, no audit, agent-hostile |
| HashiCorp Vault | Heavier operational burden, requires separate infrastructure |
| AWS Secrets Manager | Cloud-vendor-locked, not suitable for local dev |
| `.env` files with git-crypt | Still scattered across machines, no rotation, no audit |
| Docker secrets | Only works in Docker Swarm/Compose, not for local IDE agents |
| 1Password CLI | Consumer-grade, no machine identity, no programmatic rotation |

---

## Implementation

- **File:** `src/l9_graphite_memory/secrets.py`
- **Dependency:** `infisical-python>=2.0` (added to `pyproject.toml`)
- **Tests:** `tests/test_secrets.py`
- **Deprecated:** `src/l9_graphite_memory/graphiti_env_loader.py` → `_archived/`
- **Deprecated:** `config/graphiti.env.example` → `_archived/`
- **Deprecated:** `config/graphiti.env.defaults` → `_archived/`
- **Deprecated:** `scripts/init_graphiti_machine_env.sh` → `_archived/`

---

## References

- [`@quantum-l9/infisical-config`](https://github.com/Quantum-L9/infisical-config) — TypeScript reference implementation
- [Infisical Universal Auth docs](https://infisical.com/docs/documentation/platform/identities/universal-auth)
- [infisical-python on PyPI](https://pypi.org/project/infisical-python/) — v2.3.6
- [Infisical Secret Rotation](https://infisical.com/docs/documentation/platform/secret-rotation/overview)
