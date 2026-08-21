# Audit findings — Cursor-Governance repo, Claude Code bootstrap, cloud env

**Scope:** `Quantum-L9/Cursor-Governance` @ `8bc5781` · Claude Code adapter bootstrap ·
Anthropic-hosted `cloud_default` session environment
**Surface:** `L9_GOVERNANCE_SURFACE=claude-code`, `CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE=cloud_default`
**Date:** 2026-08-21 · **Status:** validated — every finding below was reproduced in-session
**Consumer:** downstream remediation. Findings are ordered by severity, each with the
command that reproduces it and the narrowest true cause.

Findings already documented as accepted posture in `docs/DEGRADED_MODE_CONTRACT.md`
are **not** listed as defects. See §3 for what was checked and found sound.

---

## 1. Findings

### F-01 · HIGH · repo · `make claude-env` fails structurally on every run

The memory-enforcement contract violates its own schema. `make claude-env` exits 1
at step 2 and never reaches `validate_capability_hosts`, `verify_account_env`, or
the `--runtime` readiness step.

```
FAIL: schema validation error: Additional properties are not allowed
      ('gate_shape', 'note' were unexpected)
On instance['preconditions']['session_prefetch']
RESULT: STRUCTURAL_FAIL — 1 issue(s)
```

**Reproduce:** `make claude-env` — or, isolated,
`.venv/bin/python environment/agents/adapters/claude-code/validate_claude_env.py`

**Cause:** commit `1632fff` ("L9 Multi-Agent Main-Bound Execution") added the
doctrine-bearing keys `gate_shape` and `note` to
`memory/memory-enforcement.contract.json` → `preconditions.session_prefetch`, and in
the same commit tightened `memory/memory-enforcement.schema.json`, but never added
those two keys to `definitions/precondition`, which is `additionalProperties: false`
with only `id` / `satisfied_by` / `established_by` / `verifies_against`.

**Remediation:** extend `definitions/precondition` to permit `gate_shape` and `note`
(both `type: string`). Keep the prose in the contract — it encodes rule 96 E7 (the
phase-lock prohibition) next to the precondition it constrains, which is where it
belongs. Do **not** relax `additionalProperties` globally; the same commit's
`test_schema_makes_phase_lock_unrepresentable` depends on that strictness.

**Verify:** `make claude-env` reaches `RESULT: PASS` on `validate_claude_env.py` and
proceeds to the runtime step.

---

### F-02 · HIGH · repo · The failure in F-01 is invisible to both tests and CI

134 adapter + main-bound conformance tests pass while the validator fails, and the
one test that would have caught it was loosened to tolerate the break rather than
the break being fixed.

**Evidence:**
- `.venv/bin/python -m pytest environment/agents/adapters/claude-code/tests/ tests/ops/scripts/test_multi_agent_main_bound.py -q` → `134 passed, 36 subtests passed`
- `environment/agents/adapters/claude-code/tests/test_validator_verdicts.py:55-67` —
  `test_never_emits_a_bare_pass` asserts `STRUCTURAL_(PASS|FAIL)`, with a docstring
  naming "a pre-existing memory-enforcement schema mismatch" as the reason it stopped
  asserting `STRUCTURAL_PASS`.
- No test anywhere invokes `validate_memory_enforcement.py`:
  `grep -rn "validate_memory_enforcement\|jsonschema" tests/ .../claude-code/tests/ ops/scripts/tests/` → no hits.
- **No CI workflow references the Claude adapter at all:**
  `grep -rn "adapters/claude-code\|claude-env\|memory_enforcement" .github/workflows/` → no hits.

**Cause:** the contract↔schema pair has no owning test, and no workflow runs the
adapter validator. The verdict-vocabulary test absorbed the regression instead of
surfacing it (rule 95, "do not weaken assertions until an incorrect result passes").

**Remediation:**
1. Add a test asserting `validate_memory_enforcement.py` exits 0 against the committed
   contract — the assertion that F-01 would have failed.
2. Add adapter validation (`make claude-env` structural step, or the two validators
   directly) to a CI workflow. `governance-self-check.yml` is the natural home.
3. Leave `test_never_emits_a_bare_pass` as the INV-8 vocabulary test it is; the new
   test in (1) carries the correctness assertion. Do not re-couple them.

**Verify:** revert F-01's schema fix locally → the new test fails; CI job fails.

---

### F-03 · HIGH · env · Health receipt reports `capabilities: READY` / `memory: READY` for a plane the repo documents as blocked

`install.sh` downgrades capability and memory status **only when
`L9_CAPABILITY_BROKER_URL` is unset**. The variable is set to a host that has no DNS
record, so a set-but-dead broker reports READY.

```
install.sh:304-307
if [ -z "${L9_CAPABILITY_BROKER_URL:-}" ]; then
  downgrade STATUS_CAPABILITIES DEGRADED "L9_CAPABILITY_BROKER_URL unset"
  downgrade STATUS_MEMORY       DEGRADED "no broker-authenticated identity path"
fi
```

**Evidence:** `.venv/bin/python ops/secrets/probe_broker.py`
```
identity:      none (hosted_surface_issues_no_session_identity)
broker dns:    no_dns_record
broker health: unreachable_URLError
PRIMARY BLOCKER: identity
```
`make claude-env` in the same session prints `capabilities=READY memory=READY`.
The comment directly above the check calls this posture "honest"; the implementation
falsifies the comment. `ops/secrets/validate_capability_hosts.py` also passes, but it
validates **syntax** only (`RESULT: PASS — every capability upstream_host is valid (syntax)`).

**Cause:** presence-of-variable is used as a proxy for reachability-and-identity.

**Remediation:** derive `STATUS_CAPABILITIES` / `STATUS_MEMORY` from
`probe_broker.py`'s classification (identity present? host resolves? health 200?) rather
than from `-z`. READY must require a verified path; `BLOCKED_BY_PLATFORM` already exists
as the correct token for this surface (exit 4) and is distinct from "no broker configured"
(exit 3) — the receipt should carry that distinction.

**Verify:** on a hosted session the receipt reads `capabilities: BLOCKED_BY_PLATFORM`,
not READY, with no change to `L9_CAPABILITY_BROKER_URL`.

---

### F-04 · HIGH · env · Graphiti group_id is unresolvable from the container root; the session hydrates zero facts and memory is read-only

The cloud container holds five repositories under `/home/user`. Group resolution scans
the workspace, matches all five, and refuses to guess.

**Reproduce:**
```bash
cd /home/user && .../.venv/bin/python ops/graphiti/graphiti_memory_client.py resolve
{"group_id": null,
 "error": "ambiguous group match: ['cursor-governance','l9-graphiti-memory','llm-router','seo-bot','website-bot'] — set GRAPHITI_GROUP_ID",
 "readonly": true}
```
From inside a single repo it resolves cleanly:
`… resolve` → `{"group_id":"cursor-governance","method":"registry","readonly":false}`

**Session impact (from the SessionStart packet):** `group_id=unresolved`, `DEGRADED`,
`facts_returned=0`, `pickup_parsed=no`, `context_chars=0`, and `readonly: true` — every
memory write for the session is refused.

**Not** a server problem: `graphiti_memory_client.py health` →
`{"mcp": {"status": "healthy", "service": "graphiti-mcp"}, "tools": {"reachable": true, "tool_count": 9}}`.

**Cause:** the hydration path resolves one group for one workspace root, and the hosted
multi-repo layout has no single workspace root.

**Remediation (pick one, in preference order):**
1. Resolve per-repository: emit one hydration packet per repo root found under the
   container root, keyed by that repo's group_id. Matches the "namespace represents
   repository identity" contract in rule 96 §3.
2. Have the bootstrap export `GRAPHITI_GROUP_ID` for the repo the session is actually
   working in, when that is determinable (e.g. from the session's designated branch or
   `CLAUDE_PROJECT_DIR`).
3. At minimum: make the ambiguous case actionable in the packet — list the resolvable
   group_ids and the exact export that fixes it, instead of a single degraded line.

**Verify:** SessionStart packet reports a concrete `group_id` and `readonly: false` in a
multi-repo container.

---

### F-05 · MEDIUM-HIGH · repo · A receipt from a *failed* hydration satisfies the memory precondition, and nothing retries for 24h

`fresh_receipt()` checks only session-id match and TTL. It does not read `degraded`
or `group_id`.

```python
# memory/memory_state.py:205-218 (fresh_receipt)
return (
    data.get("session_id") == session_id
    and (time.time() - float(data.get("created_at", 0))) < ttl
)
```

The receipt this session actually wrote:
```json
{"status": "prefetched", "degraded": true, "group_id": "unresolved", ...}
```
`grep -n "degraded\|group_id" memory/memory_state.py` returns only docstring hits.

**Scope note — this is not a request to make memory blocking.** The non-blocking gate
shape is required by rule 96 E7 / rule 98 (`fresh hydration? yes → continue; no →
hydrate, then continue`), and the contract, the schema, and
`test_contract_does_not_gate_repository_writes_on_phase_lock` all correctly enforce
that. The defect is narrower: a hydration that returned nothing is recorded as
`status: "prefetched"`, the gate treats it as satisfied, and the "no → hydrate, then
continue" branch is therefore never taken for the remaining `session_ttl_seconds`
(86400). The session runs memory-blind while every telemetry surface reports the
precondition met.

**Remediation:** have the prefetch hook write `status: "degraded"` when the hydration
packet is degraded, and have `fresh_receipt()` treat a degraded receipt as *not fresh*
— which re-attempts hydration and then **continues either way**, per the mandated gate
shape. No new blocking path.

**Verify:** with an unresolvable group, a second governed write re-attempts hydration
rather than reading the stale receipt, and still proceeds.

---

### F-06 · MEDIUM · env+governance · The live bootstrap stub is a revision that exists in no commit, and the drift check points remediation the wrong way

`~/.l9/cloud-session.env` records `L9_STUB_REVISION=2026-08-21.2`. Repo HEAD carries
`L9_STUB_REVISION="2026-08-21.1"` (`web/setup.bootstrap.sh:31`). Revision `.2` appears
in **no commit on any branch**:

```bash
git log --all -S'2026-08-21.2' -- environment/agents/adapters/claude-code/web/setup.bootstrap.sh
# (no output)
```
Both clones agree on `.1` (`/root/.cursor-governance` and `/home/user/Cursor-Governance`
are byte-identical), and `gov-refresh.json` confirms `local_sha == origin_sha == 8bc5781`.

So the Setup-script account field is running bootstrap code that is not in the SSOT.

Compounding, the drift detector is a bare inequality with a single-direction fix:
```python
# verify_account_env.py:193
"stub_drift": bool(want_rev) and have_rev != want_rev,
# :231-236 prints, unconditionally:
#   "re-paste web/setup.bootstrap.sh into the Setup script field"
```
Following that instruction here would **downgrade** the live field from `.2` to `.1`
and silently destroy the only copy of the `.2` stub.

**Remediation:**
1. Before anything else, recover the `.2` stub text from the account field and diff it
   against HEAD. If it carries real changes, commit them; if it is stale hand-editing,
   re-paste `.1` deliberately.
2. Make the check direction-aware: field **ahead** of HEAD → "the Setup field carries
   uncommitted bootstrap code; recover and commit it"; field **behind** HEAD → the
   existing re-paste instruction.

**Verify:** `verify_account_env.py` distinguishes ahead/behind and names the correct
action for each.

---

### F-07 · MEDIUM · env · Bootstrap wired `/home/user/.github`; the session's project directory is `/home/user`

`bootstrap-state.json` records `"workspace": "/home/user/.github"`. SessionStart warned:
`bootstrap wired /home/user/.github, but this project is /home/user — .claude mirrors may be missing`.

**Evidence:**
- `/home/user/.github/.claude/skills` → 51 skills (wired)
- `/home/user/.claude` → **does not exist**
- project-scope reconcile against the real project root reports all 51 skills missing:
  `.venv/bin/python ops/scripts/reconcile_claude_l9_skills.py --root /root/.cursor-governance --scope project --workspace /home/user --check` → 51 × `missing:l9-*`

**Cause:** `install.sh:47` takes `WORKSPACE="$PWD"`, and `web/setup.bootstrap.sh` runs
under whatever cwd the platform provides — the first repo in a multi-repo container, not
the session root. The consequence is masked here only because user scope
(`/root/.claude/skills`, 53 skills) resolves; on a session where user scope is absent,
project-scope skills and the `.claude/rules` mount would both be missing.

**Remediation:** in a multi-repo container, reconcile every repository root **and** the
container root, rather than a single `$PWD`. Give `install.sh` an explicit
`--workspace` list, or derive it from the repo roots present under `$HOME`.

**Verify:** `/home/user/.claude/skills` exists and the project-scope `--check` reports
zero missing.

---

### F-08 · MEDIUM · env · `cloud-session.env` unsets the platform GitHub credential, and `~/.profile` sources it unguarded

```bash
# ~/.l9/cloud-session.env, written by setup.bootstrap.sh:171
unset AWS_SECRET_ACCESS_KEY AWS_ACCESS_KEY_ID AWS_SESSION_TOKEN GITHUB_TOKEN GH_TOKEN
```
The same stub's own comment three lines above reads:
`# No GH_TOKEN export: the platform proxy injects its own credential.`
It then unsets the credential the platform injected.

**Reproduce:**
```bash
bash -c '. "$HOME/.l9/cloud-session.env"; echo "GH_TOKEN=${GH_TOKEN:+set}"'   # → GH_TOKEN=
```
**Current blast radius is narrow, and by accident:** `~/.bashrc:6` returns early for
non-interactive shells, so the `~/.bashrc:110` sourcing never fires for tool-invoked
bash — which is why this session still holds both tokens. But `~/.profile:12` sources
the file **unconditionally**, so any login shell (`bash -l`, `su -`, ssh) loses them.

**Cause:** the vault-hygiene unset list (correctly covering Infisical / AWS / Sonar /
Semgrep / Graphiti) was extended to two variables the platform legitimately provides.

**Remediation:** drop `GITHUB_TOKEN` and `GH_TOKEN` from the unset list on hosted
surfaces. The remaining unsets are correct and should stay. If a non-hosted surface
needs them cleared, guard on `CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE`.

**Verify:** `bash -lc 'echo ${GH_TOKEN:+set}'` → `set`; `gh api user` works from a login shell.

---

### F-09 · MEDIUM · repo · `make wiring-check` fails 100% of the time on any non-Cursor surface

Five FAILs, all asserting Cursor IDE wiring that will never exist in a headless
`claude-code` container:

```
FAIL: hook symlink missing: /root/.cursor/hooks/governance-backup.sh
FAIL: hooks.json missing: /root/.cursor/hooks.json
FAIL: sessionStart bootstrap not in hooks.json
FAIL: beforeSubmitPrompt skill router missing from hooks.json
FAIL: before-submit-skill-router.py missing under ~/.cursor/hooks
FAIL: afterShellExecution pr-gate-failure-shell.sh missing from hooks.json
FAIL: pr-gate-failure-shell.sh missing under ~/.cursor/hooks
RESULT: FAIL — sessionEnd hook incomplete
RESULT: FAIL — Graphiti wiring
```

**Reproduce:** `make wiring-check` (exit 2)

The script already classifies the workspace (`Workspace kind: ssot_checkout`) and
correctly skips consumer-symlink requirements on that basis. The Cursor-hook sections
simply do not consult that classification, or `L9_GOVERNANCE_SURFACE`.

**Cause:** surface-awareness exists for one section of the validator and not the others.

**Remediation:** gate the `sessionEnd governance backup hook` and the Cursor half of the
`Graphiti memory (GLOBAL-001)` section on surface — report `SKIP: cursor-plane (surface=claude-code)`
— while keeping them blocking on `cursor`. The Claude-plane equivalents are already
verified separately and pass (`.claude/settings.json` registers SessionStart, Stop,
UserPromptSubmit, PreToolUse ×3, UserPromptExpansion).

**Verify:** `make wiring-check` exits 0 on `claude-code` and still fails on `cursor`
with the Cursor hooks removed.

---

### F-10 · MEDIUM · env · `mcp: READY` is file-presence, not connectivity — the memory front door cannot resolve

`.mcp.json` registers `graphiti-memory` at `${L9_CAPABILITY_BROKER_URL}/mcp/graphiti`,
which expands to `https://broker.quantumaipartners.com/l9/capability/mcp/graphiti` — a
host with no DNS record (F-03). `install.sh` reports `STATUS_MCP=READY` on the sole
basis that `.mcp.json` exists (`say ".mcp.json already present — left as the repo committed it"`).

**Evidence:** `curl --max-time 15 https://broker.quantumaipartners.com/l9/capability/health`
→ `curl: (56) CONNECT tunnel failed, response 502`; `getent hosts broker.quantumaipartners.com` → no record.
By contrast the underlying store is reachable directly:
`curl -o /dev/null -w '%{http_code}' https://memory.quantumaipartners.com/graphiti/mcp` → `406`
(server alive, wrong Accept header), and the CLI transport is healthy (F-04).

**Remediation:** report MCP readiness from an actual handshake (or at minimum host
resolution) rather than file presence; a registered-but-unresolvable server is
DEGRADED. Track separately from F-03 — this is the front-door check, F-03 is the
capability accumulator.

**Verify:** the receipt reports `mcp: DEGRADED` while the broker host does not resolve.

---

### F-11 · LOW-MEDIUM · env · Three enforcement-sounding flags are prescribed and enforce nothing on this surface

`web/environment.env.example` prescribes them, and `verify_account_env.py` counts them
among the 36 "expected variables" that must match:

| Variable | Line | Consumers in repo |
|---|---|---|
| `L9_MEMORY_REQUIRED=true` | 73 | **0** |
| `L9_MEMORY_FAIL_CLOSED=true` | 74 | **0** |
| `GRAPHITI_WRITE_GATES=1` | 56 | 12 — all in `ops/graphiti/*`, the **Cursor** gate plane, which F-09 shows is not wired here |

**Reproduce:** `grep -rl "L9_MEMORY_REQUIRED" --include=*.py --include=*.sh --include=*.yaml . | grep -v '.venv/\|.git/\|WIP/\|docs/'` → empty.

The Claude surface gates memory through `hooks/memory_gate.py` + receipts, which read
none of these. An operator reading the environment field would reasonably conclude
memory writes fail closed on this surface. They do not (see F-05).

**Remediation:** for each — implement it on the Claude plane, remove it from the
prescribed set, or annotate it in `environment.env.example` as Cursor-plane-scoped.
Silent no-ops in a file that doubles as the contract are the problem, not the values.

---

### F-12 · LOW · env · `L9_AUTONOMY_AUTONOMOUS_MERGE=true` is prescribed for a surface where merge cannot work

`environment.env.example:82` annotates it as "a real merge_gate.py control", and line 90
sets it `true`. `docs/DEGRADED_MODE_CONTRACT.md` states, correctly, that
`gh pr merge` is GraphQL and therefore that `L9_AUTONOMY_AUTONOMOUS_MERGE=true` is
inoperative on this surface. Verified:

```
gh pr list  → HTTP 403: This GraphQL query (PullRequestList) is not enabled for this session
gh api /repos/Quantum-L9/Cursor-Governance/pulls?state=open  → 266, 265, 264 …
```

**Remediation:** carry the hosted-surface caveat into `environment.env.example` beside
the variable, or default it `false` for `cloud_default`. Documentation-only; the merge
gate itself is sound.

---

### F-13 · LOW · repo · The documented `make claude-env` diagnostic is unreachable, and the "read-only" doctor rewrites the session receipt

Two small contradictions in the entry point `CLAUDE.md` points every agent at.

1. `CLAUDE.md` says `make claude-env   # structural validation + RUNTIME readiness (exit 5 = not wired)`.
   `EXIT_RUNTIME_NOT_READY = 5` but `EXIT_STRUCTURAL_FAIL = 1`
   (`validate_claude_env.py:747-749`), and `make` aborts the target on the first
   non-zero step — so while F-01 stands, the target exits 1 and the `--runtime` step
   never runs. The advertised diagnostic cannot be observed.
2. The Makefile comment calls the target "read-only", but its first step
   (`claude-install-check`) rewrites `~/.l9/claude/bootstrap-state.json`. Observed in
   this session: SessionStart reported `skills=READY rules=READY capabilities=DEGRADED
   memory=DEGRADED`; after one `make claude-env` the same file reported
   `skills=DEGRADED rules=DEGRADED capabilities=READY memory=READY`. Four verdicts
   inverted because the two runs used different `--workspace` values and different
   environments — so the receipt describes the last check, not the running session.

**Remediation:** run the runtime step unconditionally (`-` prefix or reorder) so the
readiness verdict is always reported; and have check-mode write a separate diagnostic
receipt instead of overwriting the session's bootstrap receipt.

---

## 2. Remediation order

F-01 first — it blocks the doctor that validates everything else, and it is a
two-key schema edit. F-02 next, so the fix cannot silently regress. Then F-04 and
F-05 together (they are one story: hydration cannot resolve, and the receipt hides
it). F-03 and F-10 together (both are presence-vs-verification in the same
accumulator). F-06 needs a human with account-field access before anything is
re-pasted. F-07, F-08, F-09 are independent and can run in parallel. F-11 → F-13
are documentation/annotation and can be batched.

## 3. Checked and found sound — do not open work here

| Area | Evidence |
|---|---|
| Publish-path gate | Probed directly: `make pr` → `permissionDecision: deny` with the L4 release instructions; `git push` / `gh pr create` / `git commit` → allowed. Exactly what CANONICAL_LAW §6.2.4 and `CLAUDE.md` document. |
| PR overlap guardrail | `pr_overlap_check.py --base origin/main` → `PASS: no non-generated file overlap with open PRs`, exit 0. `gh_available()` correctly probes `gh --version`, not `gh auth status`, so the documented auth false-negative does not fail it closed. |
| Generated artifacts | `sync_generated_artifacts.py --force --check --json` → `{"errors": [], "warnings": [], "wrote": []}`. No drift. |
| Graphiti server | `health` → `mcp: healthy`, 9 tools reachable. The store is up; only group resolution is broken (F-04). |
| Adapter + conformance tests | 134 passed, 36 subtests. (They pass *around* F-01 — see F-02 — but the assertions themselves are sound.) |
| Secret hygiene | Validator confirms no committed secrets, no bearer in `mcp.template.json`, no credential in `environment.env.example`, `setup.bootstrap.sh` or `web/setup.sh`; zero-static-secret contract documented. Holds. |
| Rule projection `denied=1` | Intentional: `ops/config/llm_rules_projection.yaml` denies `84-cursor-governance-wiring` as Cursor-plugin-only. Not a defect. |
| Claude hook plane | `.claude/settings.json` registers SessionStart, Stop, UserPromptSubmit, PreToolUse ×3, UserPromptExpansion — all via `l9_hook_exec.sh`. Gates are live (a `cat .mcp.json` was denied mid-audit by the PreToolUse gate). |
| `plugins: DEGRADED` | Platform-imposed (`SKIP_PLUGIN_MARKETPLACE=true`), already handled in `install.sh` with an explicit branch. Not actionable in-repo. |
| `gh auth status` false negative | Already documented in `DEGRADED_MODE_CONTRACT.md`; `gh api` REST works. Not a defect. |
| Broker `BLOCKED_BY_PLATFORM` | Structural, documented, outside this repo. Only the *reporting* of it is a defect (F-03). |
| Audit branch base | `claude/cursor-governance-audit-qdbhlw` is at `origin/main` (`8bc5781`) with zero divergence and a clean tree. |
