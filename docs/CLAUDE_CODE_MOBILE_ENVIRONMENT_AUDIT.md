# Claude Code Mobile — environment, bootstrap, secrets and memory audit

**Audited SHA:** `91daac4a8a026917bfd2ae243827008a83866ce2` (`main`, both the SSOT clone
at `/root/.cursor-governance` and the workspace checkout at `/home/user/Cursor-Governance`;
`git ls-remote origin main` agrees, `commits_behind: 0`).

**Audit date:** 2026-09-05 · **Surface:** `claude-code`, entrypoint `remote_mobile`.

**Final status:** `VERIFIED_WITH_NON_BLOCKING_FINDINGS`.

Every claim below is backed by execution in the live container at that SHA. No secret
value, fragment, or full process environment appears anywhere in this document; secrets
are reported as name, presence, length, and a truncated non-reversible digest only.

---

## Executive verdict

The mobile bootstrap works. Gates fail closed, dependency install converges,
environment inheritance is complete and unshadowed, and no credential leaks into any
artifact. Four things previously suspected to be broken are proven correct here, and
the L4 cross-repository authorization leak named in `CLAUDE.md` is **fixed** and verified
at runtime.

What is wrong is not the mechanism but what the mechanism **reports about itself**, and
who it silently leaves out:

1. `Graphiti_authenticated_health: READY` asserts an authentication that does not exist
   on this surface and is never measured.
2. A hard cap of six roots, applied to a twelve-repository container under a stable
   ASCII sort, means the same six repositories always win and the same six always get
   **neither** memory hydration **nor** a dependency install — deterministically, every
   session, reported as a parenthetical.
3. Two readiness receipts are read as current while describing a different workspace, or
   a moment thirteen hours earlier.

None of these blocks operation. All three make a degraded state read as a ready one,
which is the specific failure this audit exists to catch.

---

## 1. Mobile runtime profile

| Dimension | Value | Source |
|---|---|---|
| OS / arch | Linux 6.18.44-fc-v24, x86_64 | `uname -srm` |
| Identity | `root`, `USER_ID=claude_code_agent` | `id -un`, env |
| `HOME` | `/root` | env |
| Workspace root | `/home/user` (**container**, not a repository) | `PWD`, `git rev-parse` fails |
| Repositories | 12 side by side under `/home/user` | `ls`, `.git` probe |
| Shell | `/bin/bash` (`/usr/bin/bash`) | `/proc/$$/exe` |
| Entrypoint | `CLAUDE_CODE_ENTRYPOINT=remote_mobile` | env |
| Remote flags | `CLAUDE_CODE_REMOTE=true`, `REMOTE_ENVIRONMENT_TYPE=cloud_default`, `CHILD_SESSION=1` | env |
| CLI version | `2.1.42` | env |
| Egress | all traffic via `http://127.0.0.1:33121`, CA `/root/.ccr/ca-bundle.crt` | env |
| System python | 3.11.15 at `/usr/local/bin/python3` | `python3 -V` |
| Locked interpreter | 3.12.3 at `$GOV/.venv/bin/python` (**not on `PATH`**, called absolutely) | probe |
| `uv` | 0.8.17 at `/root/.local/bin/uv` | readiness receipt |
| Governance SSOT | `/root/.cursor-governance` = `$HOME/.cursor-governance` | resolver |

`PATH` has 14 components and **zero duplicates**. No shell rc file
(`/root/.bashrc`, `/root/.profile`, `/etc/profile`, `/etc/bash.bashrc`) references
`L9_*`, the governance clone, or the proxy — so no rc-driven shadowing exists.

---

## 2. Startup execution graph

```
CCR sandbox container start
  └─ platform env injection ......... proxy, CA bundles, CLAUDE_CODE_*, credential sentinels
  └─ account environment field ...... GRAPHITI_*, L9_AGENT_ROLE, L9_GOVERNANCE_*,
                                      L9_MEMORY_*, PR_REMEDIATE
  └─ repository clone × 12 .......... /home/user/<repo>
  └─ governance clone ............... /root/.cursor-governance @ 91daac4
  └─ Claude Code process start
       └─ settings merge ............ /root/.claude/settings.json (user)
                                      /home/user/.claude/settings.json (project)
                                      /home/user/.claude/settings.local.json (local, wins)
       └─ SessionStart hooks, in registration order — all via l9_hook_exec.sh
            1. session_start_claude_governance.sh  (observer, 30s)
                 ├─ resolve_governance_dir → $HOME/.cursor-governance
                 ├─ cloud governance refresh → gov-refresh.json (TTL 3600s)
                 ├─ read bootstrap-state.json + readiness-receipt.json
                 └─ emit additionalContext  ← stdout only
            2. memory_prefetch.py                  (observer, 25s)
                 ├─ workspace_roots(/home/user, cap=6, predicate=own-namespace)
                 ├─ Graphiti hydrate per root
                 ├─ write /home/user/.l9/memory/receipts/<session>.json
                 └─ emit additionalContext  ← stdout only
            3. session_deps_cloud.sh               (observer, 90s)
                 ├─ workspace_roots(/home/user, cap=6)
                 ├─ per-repo manifest fingerprint → ~/.l9/claude/deps-<sha>.stamp
                 └─ install only on fingerprint miss
       └─ ready
```

**The single most load-bearing fact in this graph:** SessionStart hooks emit
`hookSpecificOutput.additionalContext` on **stdout**. They export nothing. No environment
variable in this session originates from a bootstrap script — the entire variable surface
comes from platform injection, the account field, and the settings triad. Any remediation
that tries to "export a variable from the bootstrap" cannot work here.

---

## 3. Environment variable ledger

168 variables at runtime. Material subset:

| Variable | Class | Producer | Required | Ready state | Child proc | Subagent | Verdict |
|---|---|---|---|---|---|---|---|
| `HOME` | PLATFORM | sandbox | yes | `/root` | ✓ | ✓ | PASS |
| `PATH` | PATH | sandbox | yes | 14 entries, no dupes | ✓ | ✓ | PASS |
| `HTTPS_PROXY` / `NO_PROXY` | PLATFORM | sandbox | yes | set | ✓ | ✓ | PASS |
| `SSL_CERT_FILE` + 10 CA siblings | PLATFORM | sandbox | yes | all → `ca-bundle.crt` | ✓ | ✓ | PASS |
| `CLAUDE_CODE_ENTRYPOINT` | SESSION | sandbox | yes | `remote_mobile` | ✓ | ✓ | PASS |
| `CLAUDE_CODE_REMOTE` | SESSION | sandbox | yes | `true` | ✓ | ✓ | PASS |
| `L9_GOVERNANCE_SURFACE` | REPOSITORY | settings triad | yes | `claude-code` | ✓ | ✓ | PASS |
| `L9_AUTONOMY_ENABLED` | FEATURE_FLAG | settings triad | yes | `true` | ✓ | ✓ | PASS |
| `L9_L4_LOCAL_AUTONOMY` | FEATURE_FLAG | user + local only | yes | `1` | ✓ | ✓ | PASS (see F-08) |
| `L9_WORKTREE_ISOLATION` | FEATURE_FLAG | user + local only | yes | `1` | ✓ | ✓ | PASS (see F-08) |
| `L9_AUTONOMY_STATE_DIR` | DERIVED | settings triad | yes | `~/.l9/autonomy` (literal `~`) | ✓ | ✓ | PASS — expanded correctly by consumers, see V-03 |
| `L9_GOVERNANCE_REMOTE` / `_BRANCH` | REPOSITORY | account field | yes | set | ✓ | ✓ | PASS |
| `L9_MEMORY_AGENT_ID` / `_SOURCE` | MEMORY | account field | yes | `claude-code` | ✓ | ✓ | PASS |
| `GRAPHITI_MCP_URL` | MEMORY | account field | yes | public HTTPS front door | ✓ | ✓ | PASS |
| `GRAPHITI_MEMORY_ENABLED` | MEMORY | account field | yes | `1` | ✓ | ✓ | PASS |
| `GRAPHITI_MCP_TOKEN` | SECRET | — | optional | **ABSENT** | — | ABSENT | see F-01 |
| `CONTEXT7_API_KEY` | SECRET | — | optional | **ABSENT** | — | ABSENT | see F-10 |
| `PR_REMEDIATE` | FEATURE_FLAG | account field | no | pinned `0` | ✓ | ✓ | see F-05 |
| `L9_GOVERNANCE_DIR` | DERIVED | — | no | ABSENT → default used | — | — | PASS |

### Precedence and shadowing

Effective precedence, confirmed against runtime for all 19 settings-supplied variables:

```
platform injection  →  account env field  →  user settings  →  project settings  →  settings.local.json
```

All 19 match their expected effective value. **No shadowing, no empty-over-nonempty
overwrite, no export lost across a script boundary, no order dependency.** The one
divergence between settings copies is F-08, and it is masked by `settings.local.json`.

### Child-process and subagent inheritance

| Boundary | Result |
|---|---|
| `bash -lc` (login) | full inheritance |
| `bash -c` (non-login) | full inheritance |
| `sh -c` (POSIX) | full inheritance |
| `python3` → `subprocess` | full inheritance |
| **Task subagent** | **168 / 168 variables, identical digests** |

Inheritance is total and unfiltered in every direction — see F-11 for the latent
consequence.

---

## 4. Secrets

### Source inventory

| Name | Canonical source | Loaded | Non-empty | Verdict |
|---|---|---|---|---|
| `GH_TOKEN`, `GITHUB_TOKEN` | rule 62 openclaw PAT | sentinel | 14 chars | **not a credential** |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | AWS Secrets Manager | sentinel | 14 chars | **not a credential** |
| `CLOUDSDK_AUTH_ACCESS_TOKEN` | GCP | sentinel | 14 chars | **not a credential** |
| `GRAPHITI_MCP_TOKEN` | account env proxy | ABSENT | — | plane unauthenticated |
| `CONTEXT7_API_KEY` | account env proxy | ABSENT | — | server not rendered |
| `CLAUDE_CODE_MESSAGING_TOKEN` | sandbox | present | 32 chars | platform-internal |

**Proof the five are one sentinel, not five credentials:** `GH_TOKEN`, `GITHUB_TOKEN`,
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `CLOUDSDK_AUTH_ACCESS_TOKEN` all hold a
14-character value with the identical SHA-256 prefix `f07d7417`. Five unrelated providers
cannot share one credential; a single placeholder across five names is the only reading.
This is the state `rules/62` documents.

### Authentication capability (probed, never disclosed)

| Path | Probe | Result |
|---|---|---|
| GitHub REST | `gh api user` | `cryptoxdog (User)` |
| GitHub REST | `gh api repos/Quantum-L9/Cursor-Governance` | resolves, `default=main` |
| GitHub git | `git ls-remote origin main` | returns `91daac4…` |
| GitHub CLI status | `gh auth status` | *"The token in GH_TOKEN is invalid."* |
| Graphiti | CLI `health` | `healthy: true`, circuit CLOSED, 9 tools |

`gh auth status` contradicts three working probes. `rules/62` already forbids gating on
it; this run is another dated confirmation. The credential reaching GitHub is supplied
outside this repository's control — recorded as a probe, not a theory.

### Exposure

`leakscan` over **142** files across `~/.l9`, `/home/user/.l9`, both `.claude` trees,
`.mcp.json` and `environment/generated`, matching AWS key ids, GitHub PATs, literal
`Bearer` headers, private-key blocks, Slack tokens and assigned-credential patterns:

```
scanned_files=142  hits=0
```

The rendered `.mcp.json` contains **no credential** — only `${GRAPHITI_MCP_URL}` as a
`${VAR}` reference, exactly as `mcp.template.json` requires. Memory receipts carry
group ids, packet ids and roots; no credential-shaped content. Secret hygiene: **PASS**.

---

## 5. Memory

### Taxonomy and load result

| Surface | Authority | Loader | Loaded this session |
|---|---|---|---|
| Repository instruction (`CLAUDE.md`) | rung "not a rung" | Claude Code discovery | **4 of 4 that exist** |
| `CANONICAL_LAW.md` (47 KB) | **rung 1** | none | **NOT LOADED** (F-12) |
| `AGENTS.md` (59 KB) | **rung 3** | none | **NOT LOADED** (F-12) |
| Projected rules (`.claude/rules`) | rung 4-ish | Claude Code rules loader | **33 of 52** (V-01 — correct) |
| Agent episodic (Graphiti) | CANONICAL_LAW §8 | `memory_prefetch.py` | 6 of 12 repos (F-02) |
| Operational state (`~/.l9`) | receipts | hooks | present (F-03, F-04) |
| Tool memory (`.venv`, deps stamps) | — | `session_deps_cloud.sh` | 6 of 12 repos (F-02) |

### Cold / warm / new-session behaviour

| Boundary | Behaviour | Evidence |
|---|---|---|
| Cold (container create) | full: clone, deps, projection, receipts | receipt timestamps `00:29Z` |
| Warm (this session, 13:17Z) | gov refresh re-ran; deps cache hit; memory re-hydrated | `gov-refresh.json`, deps run |
| Same shell / child shell | environment intact, memory not re-read | inheritance probes |
| Fresh session | rehydrates from Graphiti + receipts; `~/.l9` survives, container-scoped | receipt reuse |
| Fresh container | everything rebuilds from zero; no hidden prior-session dependency | cold path above |

`~/.l9` persists across sessions **within** a container and is lost with it. Nothing in
the bootstrap treats it as durable beyond that.

---

## 6. Bootstrap idempotency — PASS

Two consecutive `session_deps_cloud.sh --workspace /home/user` runs:

```
run 1: "session-deps: 6/6 repositories cached and proven — nothing to install"   3.8s
run 2: "session-deps: 6/6 repositories cached and proven — nothing to install"   3.2s
files in ~/.l9/claude:  44 → 44 → 44      (delta 0, delta 0)
```

Converges. No reinstall, no state accumulation, no duplicate `PATH` or shell-init entry.

---

## 7. Failure injection — PASS (INV-1 holds)

| Injected fault | Class | Exit | Behaviour |
|---|---|---|---|
| governance SSOT unreachable | gate | **2** | BLOCK, names the fault + repair command |
| governance SSOT unreachable | observer | 0 | skip, logged |
| locked interpreter missing | gate | **2** | BLOCK |
| malformed registration (no class) | — | **2** | refuses to guess |
| unknown class `bogus` | — | **2** | refuses |

Gates fail closed under every fault. Observers fail open and record. This is the
distinction `l9_hook_exec.sh` exists to enforce, and it holds.

---

## 8. Findings register

### F-01 · P1 · AUTHENTICATION / MEMORY — readiness asserts an authentication that does not exist

**Surface:** `ops/scripts/emit_claude_readiness.py:306`, field `Graphiti_authenticated_health`.

**Expected:** a field named `*_authenticated_health` reports whether the memory transport
is authenticated.

**Actual:** it is a verbatim alias of `memory_cli_status` (`graphiti_status, graphiti_note
= cli_status, cli_note`), whose READY reason is the hardcoded string `"cli authenticated"`.
The value measures **reachability**. In this environment there is no authentication at all:
`GRAPHITI_MCP_TOKEN` is ABSENT, the client adds `Authorization` only when that variable is
set (`graphiti_memory_client.py:226–228`), and the rendered `.mcp.json` carries `url` with
no `headers`. `mcp.template.json` states the unauthenticated posture is intentional
(`_optional_headers`, "Graphiti stays unauthenticated"), so the defect is the **label**,
not the posture.

**The same receipt contradicts itself:** `Graphiti_authenticated_health: "cli
authenticated"` sits beside `secret_boundary_status: "model-controlled (no
broker/Infisical/Graphiti secret in this environment)"`.

**Impact:** an operator reading the readiness receipt concludes the memory plane — a public
HTTPS front door exposing write tools over 11 group namespaces — is authenticated. It is not.

**Minimum fix:** rename the field to `Graphiti_reachability`, and add a distinct
`graphiti_transport_auth` field emitting `AUTHENTICATED` / `UNAUTHENTICATED` from the
presence of `GRAPHITI_MCP_TOKEN`. Do not reuse the CLI health reason string.

**Verification:** receipt shows `UNAUTHENTICATED` on this surface; a token-bearing surface
shows `AUTHENTICATED`; `tests/ops/scripts/test_emit_claude_readiness.py` asserts both.

---

### F-02 · P1 · MEMORY / PERSISTENCE — six repositories are permanently starved

**Surface:** `ops/scripts/lib/workspace_roots.py:70` (`sorted(...)[:cap]`),
`memory_prefetch.py:48` (`_MAX_HYDRATION_ROOTS = 6`), and the same helper in
`session_deps_cloud.sh`.

**Expected:** a cap bounds cost, and which roots it drops varies or is at least visible.

**Actual:** roots are `sorted()` then truncated to 6. The sort is stable ASCII, so the
winners never change. In this 12-repository container the same six always win:

```
hydrated + deps:  Cursor-Governance  PR_Repair  SEO-Bot  Website-Bot  l9-assurance  l9-ci-core
never either:     l9-ci-debt-intelligence  l9-ci-debt-lsp  l9-ci-debt-resolver
                  l9-ci-sdk  l9-harness  l9-observability-core
```

The emitted line reads *"(cap 6; repositories with no namespace of their own are skipped)"*
— naming two possible reasons, attributing neither, and listing no dropped repository. It
is materially misleading here: `graphiti health` reports **11** registered group ids,
including `l9-ci-sdk`, `l9-ci-debt-*` and `l9-harness`, so those were dropped by the **cap**,
not for want of a namespace.

**Impact:** half the constellation operates every session with no episodic memory and no
proven toolchain, and the session text implies they had nothing to hydrate.

**Minimum fix:** (a) name the dropped roots in the emitted line and state which rule dropped
each; (b) raise the cap to the repository count or rotate the window across sessions so
coverage is eventually complete.

**Verification:** in a 12-repo container the emitted line names all 6 dropped roots with a
per-root reason; over N sessions every namespaced repo hydrates at least once.

---

### F-03 · P2 · BOOTSTRAP — a single bootstrap receipt stamped with someone else's workspace

`~/.l9/claude/bootstrap-state.json` records `"workspace": "/home/user/Website-Bot"` and
`"overall": "READY"`, `ttl_seconds: 86400`. This session's workspace is `/home/user`.
One global receipt describes one arbitrary repository, and every other workspace in the
container reads that verdict as its own. `l4_local.py` already solved exactly this shape
by namespacing state per workspace slug (see V-03); this receipt did not adopt it.

**Fix:** namespace `bootstrap-state.json` per workspace, or add an explicit
`container_roots` list and refuse to answer for a workspace not in it.

---

### F-04 · P2 · READINESS — a receipt with no TTL read as current 13 hours later

`~/.l9/claude/readiness-receipt.json` has `timestamp: 2026-09-05T00:29:55+00:00` and
**no `ttl_seconds`**. SessionStart at `13:17Z` read and printed it as the capability plane.
Every field — including the F-01 authentication claim — is a statement about container
creation time. `gov-refresh.json` gets this right (`ttl_seconds: 3600`, `state: fresh`);
the readiness receipt does not. `CLAUDE.md` already warns that receipts expire and that an
absent receipt means `never_ran`, not `ready`; this artifact has no way to express either.

**Fix:** add `ttl_seconds` and a recompute-or-`unknown` read path, matching
`governance_refresh_receipt.py`.

---

### F-05 · P2 · GOVERNANCE / ENV — `PR_REMEDIATE=0` is pinned account-wide

`PR_REMEDIATE=0` is present in the ambient account environment for every invocation on this
surface. `rules/48` states remediates defaults to 1 after the PR opens and that
`PR_REMEDIATE=0` is **opt-out only**; `zz-autonomy-surface-override` repeats it. Pinned at
the account level, the documented default is unreachable — the poll-to-green worker can
never run, and no `make pr` invocation restores it without an explicit per-command override.

**Fix:** remove `PR_REMEDIATE` from the account environment field; pass it per invocation
where opt-out is actually intended.

---

### F-06 · P3 · HOOK LAUNCHER — fail-closed is decided by the caller, not by the hook

`l9_hook_exec.sh` takes `--class` from the settings registration and never checks it against
the hook's identity. Proven:

```
--class observer memory_gate.py   →  exit 0, gate did not evaluate
--class gate     memory_gate.py   →  exit 2, BLOCKING
```

The file's own header says it exists so the fail-open/fail-closed decision is made once
rather than re-typed in eight `bash -c` one-liners — but a wrong `--class` in one of those
one-liners still silently downgrades a gate to an observer, which is the copy-paste slip
the design set out to prevent.

**Fix:** a `HOOK_NAME → required class` table inside the launcher; refuse (exit 2) when the
registration disagrees.

---

### F-07 · P3 · HOOK AUDIT — the skip log is lost in the case it exists for

`record_skip()` writes under `$HOME` and returns silently on `mkdir` failure
(`mkdir -p … || return 0`). The failure injection wrote to
`/nonexistent-gov-root/.l9/claude/hook-skips.log` and vanished. An observer skip caused by a
broken `HOME` — precisely when the audit trail matters — leaves no trace.

**Fix:** fall back to `${TMPDIR:-/tmp}/l9-hook-skips.log` and name the fallback on stderr.

---

### F-08 · P3 · SETTINGS DRIFT — project-scope settings missing two governance flags

`/home/user/.claude/settings.json` omits `L9_L4_LOCAL_AUTONOMY` and `L9_WORKTREE_ISOLATION`
from `env`; `/root/.claude/settings.json` and `settings.local.json` carry both. Runtime is
correct **only** because `settings.local.json` wins. Remove that file and both gates lose
their flag at the project scope.

**Fix:** reproject the project-scope settings from `settings.template.json`; add the two
keys to the projection drift check.

---

### F-09 · P3 · RULES — an always-loaded rule depends on a path-scoped one

`80-gmp-execution` (always-loaded) closes with *"Phase closure conditions in this file
depend on the detailed testing rules in `50-qa-testing.mdc`"*. `50-qa-testing` is
path-scoped and absent unless a test file is touched, so the dependency is dangling for most
of a session.

**Fix:** inline the closure conditions `80` actually needs, or make the reference conditional.

---

### F-10 · P3 · CONTEXT7 — a mandatory rule for an absent capability

`CONTEXT7_API_KEY` is unproxied, so `_requires_env` correctly suppresses the `context7`
server, and `SKIP_PLUGIN_MARKETPLACE=true` blocks the plugin. Meanwhile `22-context7-auto-invoke`
is always-loaded and mandates a Context7 call before first implementation. The rule itself
names the fallback (skill `l9-context7-docs` or an official-docs GET), so this is a standing
obligation mismatch rather than a defect — recorded so it is not rediscovered as one.

---

### F-11 · P2 (latent) · SUBAGENT SCOPE — no environment filtering exists

A subagent receives **168 of 168** variables with identical digests, including
`CLAUDE_CODE_MESSAGING_TOKEN` and every credential-shaped name. Today nothing real leaks:
the GitHub/AWS/GCP names all hold one sentinel. But there is no filtering layer at all, so
the first real credential proxied into the account field reaches every subagent and every
child process, whatever its contract says.

**Fix:** define an explicit subagent environment allow-list before any real credential is
proxied to this surface.

---

### F-12 · P2 · MEMORY / AUTHORITY — rungs 1 and 3 never reach context

`CANONICAL_LAW.md` (47 KB) and `AGENTS.md` (59 KB) are rungs 1 and 3 of the authority chain
`CLAUDE.md` declares, and neither is a Claude memory file — neither loads. What does load is
`CLAUDE.md` itself (which states it is "not a rung") and the 33 always-apply projected rules.
The chain is in force and largely invisible, which is the condition `CLAUDE.md` was written
to mitigate rather than one it resolves.

**Fix:** project the binding clauses of `CANONICAL_LAW` and `AGENTS.md` into always-apply
rule files under `environment/generated/llm-rules/`, so authority arrives by the same path
the rest of the doctrine does.

---

## 9. Verified correct (previously suspected defects)

| # | Claim | Proof |
|---|---|---|
| V-01 | Rule projection is **not** partially broken | 33 files without `paths:` frontmatter loaded; 19 files with `paths:` withheld. Exact 33/19 split matches exactly. Path-scoped rules load on file match by design. |
| V-02 | `CLAUDE.md` hydration works on mobile | 4 of the 4 `CLAUDE.md` files that exist reached context. The historical `memory_files_completed {"file_count": 0}` is resolved. |
| V-03 | L4 cross-repository authorization leak is **fixed** | `~` expands to `/root`; receipts are workspace-namespaced with a 12-char identity digest. `Cursor-Governance-ff50192fd402` ≠ `SEO-Bot-059a2f62d9b4` — a release authorized in one repo cannot satisfy another sharing a branch name. |
| V-04 | INV-1 gate fail-closed holds | 4 injected faults, all exit 2 for gates, all exit 0 + logged for observers. |
| V-05 | Bootstrap is idempotent | 2 runs, 0 state delta, cache hit both times. |
| V-06 | No secret leaks into any artifact | 142 files scanned, 0 hits; `.mcp.json` credential-free. |
| V-07 | Environment inheritance is complete and unshadowed | 168/168 to subagents; clean across login/non-login/POSIX/python; no `PATH` dupes; no rc-file mutation. |
| V-08 | GitHub transport matches `rules/62` exactly | `gh auth status` says invalid; `gh api user` and `git ls-remote` both work. |

---

## 10. Remediation order (root-cause first)

1. **F-01** — stop asserting authentication that is not measured. Everything else in the
   readiness receipt is trustworthy; this one field is not, and it is the field an operator
   checks before trusting the memory plane.
2. **F-02** — name the dropped roots, then fix the coverage. Half the constellation is
   silently unserved; the silence is the worse half.
3. **F-04** then **F-03** — give the readiness receipt a TTL, then namespace the bootstrap
   receipt per workspace. Both are the same defect (a receipt read outside the scope it
   describes) and F-04 is the cheaper fix.
4. **F-11** — define the subagent allow-list **before** any real credential is proxied here.
   Cheap now, a P0 later.
5. **F-05** — unpin `PR_REMEDIATE`.
6. **F-06**, **F-08** — close the two silent-downgrade paths (hook class, settings drift).
7. **F-07**, **F-09**, **F-10** — audit-trail fallback, dangling rule reference, documented
   Context7 gap.

---

## 11. Unresolved UNKNOWNs

- **Server-side access control on the Graphiti front door.** No client credential is
  required from this container. Whether the host enforces IP allow-listing or another
  control cannot be determined from inside a single egress path. F-01 is scoped to the
  false label, which *is* provable here; the posture question needs a probe from outside
  this network.
- **The origin of the working GitHub credential.** `gh api` succeeds while `GH_TOKEN` is a
  sentinel. The credential is supplied outside this repository's control. `rules/62` already
  refuses to assert a mechanism the repository cannot verify; this audit does the same.
- **The exact literal of the 14-character sentinel.** Not needed: five unrelated providers
  sharing one value is sufficient proof that none is a credential.

---

## Final status

`VERIFIED_WITH_NON_BLOCKING_FINDINGS` — the mobile environment boots, authenticates to
GitHub, hydrates memory for the repositories it selects, gates fail closed, and no secret
leaks. Two P1 findings (F-01, F-02) make a partial state read as a complete one and should
be closed before the readiness receipt is trusted as evidence.
