# Audit findings — Cursor-Governance repo, Claude Code bootstrap, cloud env

**Scope:** `Quantum-L9/Cursor-Governance` @ `8bc5781` · Claude Code adapter bootstrap ·
Anthropic-hosted `cloud_default` session
**Surface:** `L9_GOVERNANCE_SURFACE=claude-code`
**Status:** every finding reproduced in-session. The **env plane is fixed** in this
branch and verified; the repo plane is open.

Findings already documented as accepted posture in `docs/DEGRADED_MODE_CONTRACT.md`
are not listed as defects. §4 lists what was checked and found sound.

---

## 1. Status

| ID | Sev | Plane | Finding | State |
|---|---|---|---|---|
| F-01 | HIGH | repo | Memory contract violates its own schema — `make claude-env` fails structurally every run | **OPEN** |
| F-02 | HIGH | repo | No test and no CI job covers that pair; the test that would have caught it was loosened | **OPEN** |
| F-03 | HIGH | env | `capabilities`/`memory` reported READY because a variable was *set* | FIXED |
| F-04 | HIGH | env | `group_id` unresolvable from the container root → 0 facts, read-only memory | FIXED |
| F-14 | HIGH | repo | Publish-path verdict depends on whether the command is piped | **OPEN** |
| F-05 | MED-HI | env | A failed hydration's receipt satisfied the memory precondition for 24h | FIXED |
| F-06 | MED | env | Live stub revision `2026-08-21.2` exists in no commit; drift check pointed the wrong way | FIXED |
| F-07 | MED | env | Container root — the session's own project dir — was never wired | FIXED |
| F-08 | MED | env | `cloud-session.env` unset `GH_TOKEN`, disabling every `gh` path in a login shell | FIXED |
| F-09 | MED | repo | `make wiring-check` asserts Cursor IDE wiring unconditionally → 100% red off Cursor | **OPEN** |
| F-10 | MED | env | `mcp: READY` was file-presence; the front door routes through a dead host | FIXED |
| F-15 | MED | repo | `merge_gate.py` matches its prohibitions against raw command text, denying documentation | **OPEN** |
| F-11 | LOW-MED | env | `L9_MEMORY_REQUIRED` / `L9_MEMORY_FAIL_CLOSED` had zero consumers | FIXED |
| F-12 | LOW | env | `L9_AUTONOMY_AUTONOMOUS_MERGE=true` where merge is documented inoperative | FIXED |
| F-13 | LOW | env | Doctor's runtime step unreachable; "read-only" doctor rewrote the session receipt | FIXED |
| F-16 | LOW | env | Prohibited credentials in the account field were never reported | FIXED |

---

## 2. Operator action required

Two account fields are copy-paste and no agent can write them. Both are now
generated from the SSOT:

| Field | Paste from | Why |
|---|---|---|
| Environment variables | `docs/account-fields/ENVIRONMENT_VARIABLES.md` | drops 3 dead flags, sets merge `false` (F-11, F-12) |
| Setup script | `docs/account-fields/SETUP_SCRIPT.md` | revision `2026-08-21.3`; stops unsetting `GH_TOKEN` (F-06, F-08) |

**Before pasting the Setup script, copy the current field out.** It holds revision
`2026-08-21.2`, which is in no commit and cannot be read back once overwritten. Diff
it against the stub and commit anything it added. `verify_account_env.py` now names
the direction so this decision is not guesswork.

Regenerate both after any change to the SSOT:

```bash
python3 environment/agents/adapters/claude-code/verify_account_env.py --emit-fields
```

---

## 3. Fixed — env plane

### F-03 · Capability and memory status was presence, not verification

`install.sh` downgraded only when `L9_CAPABILITY_BROKER_URL` was *unset*. The host
has no DNS record and the hosted surface issues no session identity, so a set-but-dead
broker reported READY — while the comment above the check called that "the honest
posture".

**Fix:** status now comes from `ops/secrets/probe_broker.py`, which already
distinguishes identity from configuration from reachability, and answers in under a
second when DNS fails.
**Verified:** `capabilities: DEGRADED`, `memory: DEGRADED`, reason `broker probe: identity`.
The URL stays configured, so this recovers by itself when the broker is deployed.

### F-04 · Memory hydrated nothing in a multi-repo container

A `group_id` identifies a repository. Resolving one from a container root matched all
five and returned none, so hydration returned `facts_returned=0` and every write was
refused `readonly: true` — with the store itself healthy (9 tools reachable).

**Fix:** `hooks/memory_prefetch.py` resolves per repository root, hydrates each under
its own namespace, and skips any that resolves to the shared cross-repo group (rules/98
reserves `igor-workspace` and `write` rejects it).
**Verified:** 0 facts → **32 facts** across `cursor-governance`, `llm-router`, `seo-bot`,
`website-bot`. The cap (6 roots) is reported in the emitted text rather than truncating
silently.

### F-05 · A failed hydration satisfied the precondition it was supposed to prove

`fresh_receipt()` checked session-id and TTL only. The receipt this session wrote read
`{"status": "prefetched", "degraded": true, "group_id": "unresolved"}` — the gate saw it
as fresh, never re-hydrated, and the session ran memory-blind for the full 24h TTL while
every surface reported the precondition met.

**Fix:** the receipt records what happened (`status: degraded`), and a degraded receipt
is not fresh — which re-runs hydration and then **continues either way**. The gate stays
non-blocking; rules/96 E7 and rules/98 require that and this does not change it.
**Verified:** receipt now `status: prefetched, degraded: False` with four groups resolved.

### F-06 · The live stub is code that is in no commit

`~/.l9/cloud-session.env` records `2026-08-21.2`; HEAD carried `.1`; `git log --all -S`
finds `.2` in no commit on any branch. The drift check was a bare `!=` that printed one
remediation — "re-paste into the Setup script field" — which here would have downgraded
production and destroyed the only copy of that code.

**Fix:** HEAD is now `2026-08-21.3`, and `revision_direction()` compares revisions as
ordered keys. *Behind* keeps the re-paste instruction; *ahead* says to copy the field out
and commit what it added, explicitly warning not to re-paste.
**Verified:** unit-checked across ahead / behind / same / unparseable.

### F-07 · The session's own project directory was never wired

Six repositories were wired; `/home/user` — the directory Claude Code loads project scope
from — was not, because `install.sh` refused any workspace that is not a git repository.
That guard was written against a different hazard (wiring the parent of a lone checkout),
and a multi-repo container root is exactly the case it misclassified.

**Fix:** `resolve_workspaces()` emits the container root, and the guard accepts a workspace
that is either `CLAUDE_PROJECT_DIR` or contains two or more repositories. Git-specific steps
already guarded on `rev-parse`, so a non-repo workspace skips them unchanged.
**Verified:** `/home/user/.claude` now exists with 51 project-scope skills, the rules mount
and settings; `settings/skills/rules` all READY.

### F-08 · The bootstrap unset the credential `gh` needs

`cloud-session.env` unset `GH_TOKEN` and `GITHUB_TOKEN`, on the reasoning that "the platform
proxy injects its own credential". Measured:

```
git ls-remote  without them -> works    (the proxy authenticates git)
gh api /user   without them -> refuses  ("please run gh auth login")
```

`~/.profile` sources that file unconditionally, so any login shell lost every `gh` path —
including the REST calls `DEGRADED_MODE_CONTRACT.md` lists as working and the open-PR
telemetry `make pr` requires before it may push.

**Fix:** neither name is swept or unset. The remaining sweep (Infisical, AWS, Sonar,
Semgrep, Graphiti) is correct and unchanged. The prohibition that still holds is on the
*field*, and F-16 now enforces it where it can actually be checked.

### F-10 · MCP readiness was file presence

`.mcp.json` registers `graphiti-memory` at `${L9_CAPABILITY_BROKER_URL}/mcp/graphiti`, and
`install.sh` reported READY because the file existed.
**Fix:** when the file routes through the broker and the broker is not READY, neither is the
front door. **Verified:** `mcp: DEGRADED — front door routes through an unavailable broker`.

### F-11 · Three flags that read as guarantees and enforced nothing

`L9_MEMORY_REQUIRED` and `L9_MEMORY_FAIL_CLOSED` had **zero** consumers anywhere in the repo.
`GRAPHITI_WRITE_GATES=1` has consumers, but only in the Cursor gate plane reached through
`~/.cursor/hooks.json`, which this surface does not install.
**Fix:** all three removed from the prescribed set, each with a comment saying why, so they
are not re-added as an obvious omission.

### F-12 · An affordance that always failed at the last step

`L9_AUTONOMY_AUTONOMOUS_MERGE=true` where `gh pr merge` is a GraphQL mutation the session
gateway does not serve. **Verified:** `gh pr list` → `HTTP 403`, `gh api .../pulls` → works.
**Fix:** `false`, with the hosted-surface reason recorded beside it and the self-hosted case
noted.

### F-13 · The doctor suppressed its own most useful output, and rewrote what it measured

`make claude-env` aborted on the first non-zero step, so a structural failure took the
RUNTIME verdict down with it — and runtime is the half that answers "was any of this loaded
into this session?". The documented `exit 5` was therefore unreachable whenever anything
structural was red. Separately, `--check` overwrote `~/.l9/claude/bootstrap-state.json`;
four component verdicts inverted between a SessionStart read and a post-doctor read.

**Fix:** every step runs and the runtime verdict always prints; structural failure still
decides the exit code. Check mode writes `bootstrap-check.json`.
**Verified:** `RUNTIME: DEGRADED` printed despite the F-01 structural failure; session
receipt byte-identical after a full doctor run.

### F-16 · A pasted credential was never reported

`DELIBERATELY_ABSENT` filtered prohibited names out of the expected set, so their *absence*
was not reported as missing — but their *presence* was not reported either, though the
docstring claimed presence was the drift.
**Fix:** `prohibited_present()` reports them by name, never by value, exempting the platform's
`proxy-injected` sentinel. That exemption is not cosmetic: `AWS_ACCESS_KEY_ID` and
`AWS_SECRET_ACCESS_KEY` both carry it on this surface, and reporting them would cry wolf on
every session.

**Validation for all of the above:** 802 tests pass (`environment/agents/adapters/claude-code/tests/`,
`tests/ops/`, `ops/scripts/tests/`, `tests/ops/scripts/test_multi_agent_main_bound.py`).

---

## 4. Open — repo plane

### F-01 · HIGH · The contract violates its own schema

```
FAIL: schema validation error: Additional properties are not allowed
      ('gate_shape', 'note' were unexpected)
On instance['preconditions']['session_prefetch']
```

Commit `1632fff` added those two doctrine-bearing keys to
`memory/memory-enforcement.contract.json` and tightened
`memory-enforcement.schema.json` in the same change, without adding them to
`definitions/precondition` (`additionalProperties: false`).

**Fix:** permit `gate_shape` and `note` (both `type: string`) in that definition. Keep the
prose in the contract — it encodes rules/96 E7 beside the precondition it constrains. Do not
relax `additionalProperties` globally; `test_schema_makes_phase_lock_unrepresentable` depends
on that strictness.

### F-02 · HIGH · Nothing covers that pair

134 adapter and conformance tests pass while the validator fails. No test invokes
`validate_memory_enforcement.py`; **no CI workflow references the Claude adapter at all**. The
test that would have caught it — `tests/test_validator_verdicts.py:55` — was relaxed to accept
`STRUCTURAL_(PASS|FAIL)`, its docstring naming the mismatch as the reason.

**Fix:** add a test asserting `validate_memory_enforcement.py` exits 0; add adapter validation
to a workflow (`governance-self-check.yml` is the natural home). Leave the verdict test as the
vocabulary test it is — do not re-couple them.

### F-14 · HIGH · The publish-path verdict depends on shell plumbing

| Command | Verdict |
|---|---|
| `git push -u origin mybranch` | allow |
| `git push -u origin mybranch \| tail -8` | **deny** — "not a sanctioned way to reach GitHub" |
| `gh pr create --fill` | allow |
| `gh pr create --fill \| tee /tmp/x` | **deny** |

`local_execution_gate.py:304` exempts the event when `event_is_git_or_gh()` is true, before
the publish-path check at line 320. `command_is_git_or_gh()` requires every segment head to be
git/gh or neutral, so a pipe drops the exemption. Both surfaces behave identically
(`main_cursor_shell` via `payload_is_git_or_gh`), so this is not an asymmetry.

The rule therefore enforces nothing — omit the pipe and it allows — while producing confident
false denials on ordinary usage. Three documents disagree about what it does:
`zz-autonomy-surface-override` §2a says denied at every phase; `CLAUDE.md` says not denied;
the gate says denied iff piped.

**Fix — decide the intent first.** Deny: evaluate the publish-path check before the exemption,
and correct `CLAUDE.md`. Allow (the CANONICAL_LAW §6.2.4 position): stop applying the check to
commands whose git/gh segments are the publishing ones, and correct the rule. Either way the
same push must get the same verdict piped and unpiped.

### F-15 · MED · `merge_gate.py` matches prohibitions against raw command text

The same input, through the two gates in `ops/autonomy/`:

| Command | `merge_gate` | `local_execution_gate` |
|---|---|---|
| heredoc whose body documents `gh pr merge --admin` | **DENY** | allow |
| `echo '# never gh pr merge --admin'` | **DENY** | allow |
| heredoc whose body documents `git push --force` | **DENY** | allow |
| a real `gh pr merge 12 --admin` | DENY | DENY |
| a real `git push --force origin main` | allow | DENY |

`merge_gate.py:85-88` regexes the whole command string, so quoted arguments and heredoc bodies
count as invocations. `local_execution_gate.py` already solved this in the same directory —
`strip_heredoc_bodies` plus `segment_head`, documented as "`echo 'git push'` is data, not a
push". This blocked two ordinary documentation writes during this audit.

The last row is not an escape: `local_execution_gate` denies the real forced push, so the effect
stays blocked. It does mean `merge_gate`'s bash matchers are both over-broad on text and not the
control that enforces.

**Fix:** run `merge_gate`'s bash matchers over `strip_heredoc_bodies` + command-position
segments, as its neighbour does.

### F-09 · MED · `make wiring-check` is red by construction off Cursor

Five FAILs, all asserting `~/.cursor/hooks.json` and Cursor hook symlinks, on a headless
container where Cursor will never run. The script already classifies workspace kind
(`ssot_checkout`) and skips consumer-symlink requirements on that basis; the Cursor-hook
sections do not consult it or `L9_GOVERNANCE_SURFACE`.

**Fix:** report those sections as skipped when the surface is not `cursor`, keeping them
blocking when it is. The Claude-plane equivalents are verified separately and pass.

---

## 5. Checked and found sound — do not reopen

| Area | Evidence |
|---|---|
| L4 release gate | `make pr` → deny with the release sequence; `git commit` → allow. Behaves as CANONICAL_LAW §6.2.4 documents. The publish-*path* rule layered on it does not (F-14). |
| PR overlap guardrail | `PASS: no non-generated file overlap`, exit 0. `gh_available()` probes `gh --version`, so the documented auth false-negative does not fail it closed. |
| Generated artifacts | `sync_generated_artifacts.py --force --check --json` → `{"errors": [], "warnings": [], "wrote": []}`. |
| Graphiti server | `health` → `mcp: healthy`, 9 tools. The store was never the problem (F-04). |
| Secret hygiene | No committed secrets; no bearer in `mcp.template.json`; no credential in the stub, `web/setup.sh`, or the variables file. |
| Rule projection `denied=1` | Intentional — `84-cursor-governance-wiring` is Cursor-plugin-only. |
| Claude hook plane | SessionStart, Stop, UserPromptSubmit, PreToolUse ×3, UserPromptExpansion all registered and live. |
| `plugins: DEGRADED` | Platform-imposed (`SKIP_PLUGIN_MARKETPLACE=true`), already branched for in `install.sh`. |
| `gh auth status` false negative | Documented in `DEGRADED_MODE_CONTRACT.md`; `gh api` REST works. |
| Broker `BLOCKED_BY_PLATFORM` | Structural and outside this repo. Only its *reporting* was a defect (F-03). |
