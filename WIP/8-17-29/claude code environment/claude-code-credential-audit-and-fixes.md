# Credential & Environment Variable Audit — Remediation Plan

**Environment:** Claude Code on the web, remote execution sandbox (ephemeral container)
**Workspace:** `/home/user` — 9 Quantum-L9 repositories
**Date:** 2026-08-17
**Method:** every finding below was verified by an executable probe, not inferred from variable names
**Disclosure:** no secret values appear in this document; only lengths, prefixes, and HTTP status codes

---

## TL;DR

One fix has disproportionate leverage:

> **Set `NODE_AUTH_TOKEN` to a classic GitHub PAT with `read:packages`.**
> It is the sole reason `npm ci`, `npm run verify:package`, and isolated consumer proofs cannot run locally in this sandbox.

Two further variables (`PERPLEXITY_API_KEY`, `OPENROUTER_API_KEY`) clear the remaining validation gap for campaign 7-ROUTER.

The AWS + Infisical vault chain is **structurally unusable** in this environment and is best bypassed rather than repaired. Reasoning in [Fix 3](#fix-3--bypass-the-vault-chain-in-this-environment).

---

## 1. Verified status

### 1.1 Working

| Credential | Evidence |
|---|---|
| `GH_TOKEN` — GitHub API (repo-scoped) | `GET /repos/Quantum-L9/LLM-Router` → **200** |
| `GH_TOKEN` — git over HTTPS | `git push` and PR open both succeeded, via 3 proxy-injected `GIT_CONFIG_KEY_*` entries |
| `GRAPHITI_MCP_TOKEN` | MCP `status: healthy`, 9 tools reachable, group resolves to `llm-router` |
| Agent proxy | `enabled: true`, port `40779`, `recentRelayFailures: []` |

### 1.2 Broken

| # | Credential | Symptom | Verified root cause |
|---|---|---|---|
| B1 | `NODE_AUTH_TOKEN` | **Absent.** `npm ci` → `E401 … authentication token not provided` | `.npmrc:2` interpolates `${NODE_AUTH_TOKEN}`; nothing sets it |
| B2 | `GH_TOKEN` for GitHub Packages | `npm.pkg.github.com` → **403** `Permission permission_denied: The token provided does not match expected scopes.` | Fine-grained PAT (`github_pat_`, 93 chars) without package read. **Not fixable by re-scoping** — see [§2](#2-correction-gh_token-cannot-be-fixed-by-re-scoping) |
| B3 | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Both are the literal 14-char string `proxy-injected` | Placeholders, not keys. A real key ID is 20 chars beginning `AKIA`/`ASIA`. `AWS_REGION` also absent; neither `aws` CLI nor `boto3` installed |
| B4 | `CLOUDSDK_AUTH_ACCESS_TOKEN` | Identical `proxy-injected` sentinel | Same as B3. No `gcloud` installed |
| B5 | Infisical UA (`INFISICAL_CLIENT_ID`, `_CLIENT_SECRET`, `_PROJECT_ID`) | UA login → **401** `UnauthorizedError: Invalid credentials` | All three match a placeholder text pattern; lengths 35 / 39 / 33, none a valid 36-char UUID |
| B6 | Governance secret resolver | `resolve_secret.py --check` → `FAIL` (exit 1)<br>`sync_secrets_registry.py` → `AWS_CLI_NOT_FOUND` | Both vault paths down simultaneously (B3 + B5) |
| B7 | `L9_CAPABILITY_BROKER_URL` | Absent | Referenced by `/root/.cursor-governance/.mcp.json`. **Not load-bearing** — the active `/home/user/.mcp.json` resolves cleanly |
| B8 | Provider keys | `PERPLEXITY_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY` all absent | No vault fallback available (B6). Cause of `REAL_PROVIDER_SMOKE_BLOCKED` in campaign 7-ROUTER |

### 1.3 Confirmed *not* a credential problem

`graphiti hydrate … DEGRADED / no repo match` at session start is a **working-directory scope** issue, not authentication.

- From `/home/user` (multi-repo root): no registry match → DEGRADED
- From `/home/user/LLM-Router`: resolves `group_id: llm-router`, `method: registry`

The same root cause explains why phase-lock acquisition only satisfied the write gate once run from the repository directory rather than the workspace root — the lock artifact is written under a cwd-derived state root.

---

## 2. Correction: `GH_TOKEN` cannot be fixed by re-scoping

An earlier reading of B2 as a plain missing-scope problem is incomplete and would send you down a dead end.

```
GET https://api.github.com/orgs/Quantum-L9/packages?package_type=npm  →  403

{"message":"This GitHub API path is not available: sessions are bound to
 their configured repositories. Use repository-scoped endpoints
 (repos/{owner}/{repo}/...)."}
```

That response comes from **Anthropic's session broker**, not GitHub. This session's `api.github.com` traffic is deliberately narrowed to the 9 configured repositories. Adding `read:packages` to this PAT changes nothing, because the broker rejects the path before GitHub evaluates any scope.

Critically, the two endpoints behave differently:

| Endpoint | Mediation | Implication |
|---|---|---|
| `api.github.com` | Broker-mediated, repo-scoped | Cannot be widened from inside the session |
| `npm.pkg.github.com` | Passes through to GitHub (its 403 body is genuine GitHub) | **A separate token supplied as an env var will work** |

This is what makes [Fix 1](#fix-1--node_auth_token-highest-leverage) viable.

---

## 3. Remediation

### Fix 1 — `NODE_AUTH_TOKEN` (highest leverage)

**Effort:** ~5 minutes · **Unblocks:** `npm ci`, `verify:package`, `verify:all`, isolated consumer proofs

1. Create a **classic** GitHub PAT with a single scope: `read:packages`.
   GitHub's documented credential for `npm.pkg.github.com` is a classic PAT. Fine-grained PAT support for that registry is inconsistent, so classic is the reliable choice — and `read:packages` alone is a narrower grant than the existing agent PAT already carries elsewhere.
2. Add it as environment variable `NODE_AUTH_TOKEN` in the environment settings at <https://claude.ai/code>.

No repository change is required — `.npmrc:2` already interpolates the variable.

**Verify:**

```bash
cd /home/user/LLM-Router
npm ci
npm run verify:package
```

**Governance note.** `CANONICAL_LAW.md` §14 designates `openclaw-igorbot/github#token` as the sole agent GitHub PAT. §14 governs the *GitHub API automation* credential; a read-only package-registry token is a distinct capability. Confirm with the owner of that law before adopting, rather than treating this document as authorization.

---

### Fix 2 — Provider keys

Add as environment variables:

| Variable | Purpose |
|---|---|
| `PERPLEXITY_API_KEY` | Search-plane provider |
| `OPENROUTER_API_KEY` | General + vision plane provider |
| `DEEPSEEK_API_KEY` | Optional — only for the Claude-Code-via-DeepSeek path |

The first two clear `REAL_PROVIDER_SMOKE_BLOCKED` for campaign 7-ROUTER and allow the non-search / search smoke proofs to execute.

---

### Fix 3 — Bypass the vault chain in this environment

**Recommendation: do not repair it here.**

The `l9-aws-secrets` flow bootstraps Infisical Universal Auth credentials **out of AWS Secrets Manager**. In this sandbox that chain is broken at every link simultaneously:

- AWS requires a CLI that is not installed, with keys that are the literal string `proxy-injected`
- `proxy-injected` is **not** the proxy brokering real credentials. `/root/.ccr/README.md` covers only TLS/CA material (`AWS_CA_BUNDLE`, `PIP_CERT`, `JAVA_TOOL_OPTIONS`, …) and documents no credential relay. Every real AWS call fails signature verification
- Infisical UA credentials are placeholder text (B5), so the fallback path is equally dead

Repairing it means four moving parts — `awscli`, `boto3`, real IAM keys, real Infisical UA credentials — inside an ephemeral container, in order to retrieve roughly five secrets.

Setting those five secrets directly as environment variables is simpler and has a smaller blast radius. **The vault chain earns its complexity on a long-lived developer machine; it does not here.**

<details>
<summary>If you repair it anyway — minimum requirements</summary>

- `awscli` and `boto3` installed via the setup script (see Fix 4)
- Real `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_REGION=us-east-1`
- Replace all three Infisical placeholders with genuine Universal Auth values
- Re-verify: `python3 ops/secrets/resolve_secret.py --ref 'openclaw-igorbot/github#token' --check` must exit 0

</details>

---

### Fix 4 — Persist tooling repairs in the environment setup script

Two Python packages were installed manually this session to un-break the Graphiti phase-lock, which gates **every governed git write**. They landed in `/usr/local/lib/python3.11/dist-packages` and the governance venv — **both are destroyed when the container is reclaimed.** Without this fix, every future session hits the identical wall.

```bash
#!/usr/bin/env bash
set -euo pipefail

# Graphiti phase-lock dependencies.
# Without these, memory_lock.py fails and every governed git write is blocked.
GOV="${HOME}/.cursor-governance"
if [ -d "$GOV/.venv" ]; then
  "$GOV/.venv/bin/python3" -m ensurepip --upgrade >/dev/null 2>&1 || true
  "$GOV/.venv/bin/python3" -m pip install --quiet pydantic pyyaml
fi
python3 -m pip install --quiet --break-system-packages pydantic pyyaml
```

**Failure signature this prevents:**

```
RuntimeError: graphiti phase-lock failed:
  File ".../ops/graphiti/episode_contract.py", line 10
    from pydantic import BaseModel, ...
ModuleNotFoundError: No module named 'pydantic'
```

---

### Fix 5 — Minor cleanup

| Variable | Action | Priority |
|---|---|---|
| `AWS_REGION` | Set to `us-east-1` | Only if taking the Fix 3 repair path |
| `L9_CAPABILITY_BROKER_URL` | Populate or remove the reference in `/root/.cursor-governance/.mcp.json` | Low — not load-bearing this session |

---

### Fix 6 — Graphiti hydration scope (not a credential fix)

Resolve the `no repo match` degradation by either:

- **(a)** making the SessionStart hook resolve the Graphiti group per-repository rather than from the workspace root, or
- **(b)** adding a `/home/user` multi-repo entry to `ops/graphiti/group_registry.yaml`

Option (a) is preferable: it also fixes the phase-lock state-root mismatch, where a lock acquired from one directory does not satisfy a write gate evaluated from another.

---

## 4. Verification checklist

Run after applying fixes. Each line must pass before the corresponding gate can be claimed.

```bash
# Fix 1
cd /home/user/LLM-Router && npm ci                    # expect: no E401
npm run verify:package                                # expect: "Package smoke passed"
npm run verify:all                                    # expect: full green

# Fix 2
node -e 'for (const k of ["PERPLEXITY_API_KEY","OPENROUTER_API_KEY"])
  console.log(k, process.env[k] ? "SET" : "ABSENT")'

# Fix 3 (only if repaired)
cd /root/.cursor-governance
python3 ops/secrets/resolve_secret.py --ref 'openclaw-igorbot/github#token' --check   # expect exit 0

# Fix 4 (in a fresh session, before any manual install)
python3 -c "import pydantic, yaml; print('deps present')"
cd /home/user/LLM-Router && python3 \
  /root/.cursor-governance/environment/agents/adapters/claude-code/hooks/memory_lock.py status

# Fix 6
cd /home/user/LLM-Router && python3 \
  /root/.cursor-governance/ops/graphiti/graphiti_memory_client.py resolve   # expect group_id: llm-router
```

---

## 5. Priority summary

| Priority | Fix | Effort | Unblocks |
|---|---|---|---|
| **P0** | Fix 1 — `NODE_AUTH_TOKEN` | ~5 min | Local `npm ci`, `verify:package`, `verify:all`, consumer proofs |
| **P1** | Fix 4 — setup script | ~5 min | All governed git writes in every future session |
| **P1** | Fix 2 — provider keys | ~5 min | Real-provider smoke proofs |
| **P2** | Fix 6 — Graphiti scope | ~30 min | Clean session-start hydration; phase-lock consistency |
| **P3** | Fix 3 — vault chain | hours | Nothing not already covered by P0–P1 (**recommend skipping**) |
| **P3** | Fix 5 — cleanup | ~2 min | Config hygiene |

---

## Appendix A — Probe commands used

Reproduce any finding with these. None emits a secret value.

```bash
# Set vs empty vs absent, by name only
for v in NODE_AUTH_TOKEN GH_TOKEN PERPLEXITY_API_KEY OPENROUTER_API_KEY AWS_REGION; do
  [ -n "${!v+x}" ] && echo "$v SET" || echo "$v ABSENT"
done

# Token type from prefix
node -e 'const v=process.env.GH_TOKEN||"";
  console.log(v.startsWith("github_pat_") ? "fine-grained PAT" : v.slice(0,4), v.length);'

# Sentinel detection
node -e 'const a=process.env.AWS_ACCESS_KEY_ID;
  console.log(a === process.env.AWS_SECRET_ACCESS_KEY
    && a === process.env.CLOUDSDK_AUTH_ACCESS_TOKEN ? JSON.stringify(a) : "differ");'

# GitHub API vs Packages registry — distinguishes broker 403 from GitHub 403
curl -sS -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $GH_TOKEN" \
  https://api.github.com/repos/Quantum-L9/LLM-Router
curl -sS -H "Authorization: Bearer $GH_TOKEN" \
  https://npm.pkg.github.com/@quantum-l9%2fgraphiti-memory-client

# Infisical Universal Auth
curl -sS -o /dev/null -w "%{http_code}\n" -X POST \
  "${INFISICAL_SITE_URL}/api/v1/auth/universal-auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"clientId\":\"$INFISICAL_CLIENT_ID\",\"clientSecret\":\"$INFISICAL_CLIENT_SECRET\"}"

# Proxy capability surface
curl -sS "$HTTPS_PROXY/__agentproxy/status"

# Graphiti — run from a repository directory, not the workspace root
cd /home/user/LLM-Router
python3 /root/.cursor-governance/ops/graphiti/graphiti_memory_client.py health
python3 /root/.cursor-governance/ops/graphiti/graphiti_memory_client.py resolve
```

---

## Appendix B — Local workaround currently in place

Because `NODE_AUTH_TOKEN` is absent, `@quantum-l9/graphiti-memory-client` could not be installed from GitHub Packages. A hand-written stub exposing only the surface consumed by `src/memory.ts` (`renderHydration`, `GraphitiMemoryClient`, `MemoryClass`) was placed at:

```
/home/user/LLM-Router/node_modules/@quantum-l9/graphiti-memory-client/
```

**Properties:** never committed (inside gitignored `node_modules`), never published, marked `private: true`, and destroyed with the container.

**Applying Fix 1 removes the need for it entirely.** Any future session lacking `NODE_AUTH_TOKEN` will require the same workaround, so treat its continued existence as a signal that Fix 1 is still outstanding.

---

## Appendix C — Facts deliberately not asserted

Stated here so this document is not mistaken for broader assurance than it provides.

- **Whether a new classic PAT will authenticate against `npm.pkg.github.com`** — not proven, as no such token was available to test. The inference rests on that endpoint not being broker-mediated (its 403 body is genuine GitHub) plus GitHub's documented guidance. Confidence: high, not verified.
- **Whether `1.2.0` of `@quantum-l9/llm-router` already exists on the registry** — unverifiable from this sandbox for exactly the reasons in B2. Must be confirmed before tagging `v1.2.0`; published versions are immutable.
- **Current GitHub behaviour for fine-grained PATs against the npm registry** — support has been evolving and sits near the assistant's knowledge cutoff. The classic-PAT recommendation is chosen to be robust either way.
