# Open findings — Cursor-Governance repo, Claude Code bootstrap, cloud env

**Scope:** `Quantum-L9/Cursor-Governance` · Claude Code adapter · Anthropic-hosted
`cloud_default` session
**Surface:** `L9_GOVERNANCE_SURFACE=claude-code`
**Status:** all five re-verified against branch HEAD. The ten env-plane findings are
fixed and removed from this document; they are in the branch history.

| ID | Sev | Finding |
|---|---|---|
| F-01 | HIGH | Memory contract violates its own schema — `make claude-env` fails structurally every run |
| F-02 | HIGH | No test and no CI job covers that pair; the test that would have caught it was loosened |
| F-14 | HIGH | Publish-path verdict depends on whether the command is piped |
| F-15 | MED | `merge_gate.py` matches its prohibitions against raw command text, denying documentation |
| F-09 | MED | `make wiring-check` asserts Cursor IDE wiring unconditionally → 100% red off Cursor |

**Order:** F-01 first — it is a two-key schema edit and it blocks the doctor that
validates everything else. F-02 immediately after, so the fix cannot silently regress.
F-14 needs a decision (deny or allow) before any code changes. F-15 and F-09 are
independent.

---

## F-01 · HIGH · The contract violates its own schema

```
FAIL: schema validation error: Additional properties are not allowed
      ('gate_shape', 'note' were unexpected)
On instance['preconditions']['session_prefetch']
RESULT: FAIL - 1 problem(s)
```

**Reproduce:** `.venv/bin/python environment/agents/adapters/claude-code/validate_memory_enforcement.py`

Commit `1632fff` added those two doctrine-bearing keys to
`memory/memory-enforcement.contract.json` and tightened
`memory-enforcement.schema.json` in the same change, without adding them to
`definitions/precondition`, which is `additionalProperties: false` over
`id` / `satisfied_by` / `established_by` / `verifies_against`.

**Fix:** permit `gate_shape` and `note` (both `type: string`) in that definition. Keep
the prose in the contract — it encodes rules/96 E7 beside the precondition it
constrains. Do not relax `additionalProperties` globally;
`test_schema_makes_phase_lock_unrepresentable` depends on that strictness.

**Verify:** `make claude-env` reaches `RESULT: PASS` on the structural validator.

---

## F-02 · HIGH · Nothing covers that pair

The adapter and conformance suites pass while the validator fails, and the test that
would have caught it was relaxed rather than the break being fixed.

**Reproduce:**
- `grep -rn "validate_memory_enforcement" tests/ environment/agents/adapters/claude-code/tests/ ops/scripts/tests/` → no hits
- `grep -rn "adapters/claude-code\|claude-env\|memory_enforcement" .github/workflows/` → **no hits at all**
- `environment/agents/adapters/claude-code/tests/test_validator_verdicts.py:55` — `test_never_emits_a_bare_pass` asserts `STRUCTURAL_(PASS|FAIL)`, its docstring naming the mismatch as why it stopped asserting `STRUCTURAL_PASS`

**Fix:**
1. Add a test asserting `validate_memory_enforcement.py` exits 0 against the committed
   contract — the assertion F-01 would have failed.
2. Add adapter validation to a workflow; `governance-self-check.yml` is the natural home.
3. Leave the verdict test as the INV-8 vocabulary test it is. Do not re-couple them.

**Verify:** revert F-01's schema fix locally → the new test fails, and CI fails.

---

## F-14 · HIGH · The publish-path verdict depends on shell plumbing

| Command | Verdict |
|---|---|
| `git push -u origin mybranch` | allow |
| `git push -u origin mybranch \| tail -8` | **deny** — "not a sanctioned way to reach GitHub" |
| `gh pr create --fill` | allow |
| `gh pr create --fill \| tee /tmp/x` | **deny** |

`local_execution_gate.py:304` exempts the event when `event_is_git_or_gh()` is true,
*before* the publish-path check at line 320. `command_is_git_or_gh()` requires every
segment head to be git/gh or neutral, so a pipe to `tail` / `cat` / `tee` drops the
exemption and the command falls through to `command_bypasses_publish_path()`. Both
surfaces behave identically (`main_cursor_shell` via `payload_is_git_or_gh`), so this is
not a surface asymmetry.

The rule therefore enforces nothing — anyone bypassing `make pr` simply omits the pipe —
while producing confident false denials on ordinary usage. Three documents disagree, and
none describes the behavior:

- `rules/zz-autonomy-surface-override` §2a — "denied at **every** phase"
- `CLAUDE.md`, under "The three things most often got wrong here" — "Raw `git push` is
  *not* denied … it will not [error]"
- the gate — denied iff piped

**Fix — decide the intent first, then make the verdict plumbing-independent.**
*Deny:* evaluate `command_bypasses_publish_path()` before the git/gh exemption, and
correct `CLAUDE.md`. *Allow* (the CANONICAL_LAW §6.2.4 position — git and gh answer to
`git_guardrails.py` by effect, and `make pr` is preferred because it runs the checkers):
stop applying the check to commands whose git/gh segments are the publishing ones, and
correct the rule. Do not leave it split.

**Verify:** a parametrized test asserting that for `git push`, `gh pr create` and
`gh pr edit`, the bare form and the `| tail -1` form return the identical verdict.

---

## F-15 · MED · `merge_gate.py` matches prohibitions against raw command text

The same input through the two gates in `ops/autonomy/`:

| Command | `merge_gate` | `local_execution_gate` |
|---|---|---|
| heredoc whose body documents a forbidden admin merge | **DENY** | allow |
| `echo` of a comment naming that same form | **DENY** | allow |
| heredoc whose body documents a forced push | **DENY** | allow |
| a real admin merge | DENY | DENY |
| a real forced push | allow | DENY |

`merge_gate.py:85-88` regexes the whole command string, so quoted arguments and heredoc
bodies count as invocations. `local_execution_gate.py` already solved this in the same
directory — `strip_heredoc_bodies` plus `segment_head`, documented as "`echo 'git push'`
is data, not a push". This blocked two ordinary documentation writes during the audit.

The last row is not an escape: `local_execution_gate` denies the real forced push, so the
effect stays blocked. It does mean `merge_gate`'s bash matchers are both over-broad on
text and not the control that enforces.

**Fix:** run those matchers over `strip_heredoc_bodies` + command-position segments, as
its neighbour does.

**Verify:** the probe table above, with rows 1–3 flipping to allow and 4 unchanged.

---

## F-09 · MED · `make wiring-check` is red by construction off Cursor

Five FAILs, all asserting `~/.cursor/hooks.json` and Cursor hook symlinks, on a headless
container where Cursor will never run:

```
FAIL: hooks.json missing: ~/.cursor/hooks.json
FAIL: sessionStart bootstrap not in hooks.json
FAIL: beforeSubmitPrompt skill router missing from hooks.json
FAIL: afterShellExecution pr-gate-failure-shell.sh missing from hooks.json
RESULT: FAIL — Graphiti wiring
```

The script already classifies workspace kind (`ssot_checkout`) and correctly skips
consumer-symlink requirements on that basis. The Cursor-hook sections consult neither
that classification nor `L9_GOVERNANCE_SURFACE` — `check_governance_wiring.sh:92` pins
`HOOKS_JSON` unconditionally.

**Fix:** report those sections as skipped when the surface is not `cursor`, keeping them
blocking when it is. The Claude-plane equivalents are verified separately and pass.

**Verify:** `make wiring-check` exits 0 on `claude-code` and still fails on `cursor` with
the Cursor hooks removed.

---

## Still outstanding for the operator

Two account fields are copy-paste and no agent can write them. Both are generated from
the SSOT by `verify_account_env.py --emit-fields`:

| Field | Paste from | Live vs HEAD |
|---|---|---|
| Environment variables | `docs/account-fields/ENVIRONMENT_VARIABLES.md` | not yet pasted |
| Setup script | `docs/account-fields/SETUP_SCRIPT.md` | live `2026-08-21.2`, HEAD `2026-08-21.3` |

**Copy the current Setup script field out before pasting.** Revision `2026-08-21.2` is in
no commit and cannot be read back once overwritten.

## Do not reopen — checked and found sound

L4 release gate · PR overlap guardrail · generated-artifact sync · Graphiti server health
(9 tools) · secret hygiene across stub, templates and variables file · rule projection
`denied=1` (intentional: `84-cursor-governance-wiring` is Cursor-only) · Claude hook plane
· `plugins: DEGRADED` (platform-imposed) · `gh auth status` false negative (documented) ·
broker `BLOCKED_BY_PLATFORM` (structural, outside this repo — only its reporting was a
defect, now fixed).
