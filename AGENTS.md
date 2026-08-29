# AGENTS.md — L9 Governance (Cursor-Governance)

Operating rules for any agent working **in** this repository, and the activation
contract for any agent working **in a repo that consumes** this repository.

Read this file before touching activation, hooks, or symlink wiring.

Authority order: `CANONICAL_LAW.md` > `ops/autonomy/surface_profile.yaml` >
this file > skills. Agent-invented contracts are lowest.

---

## 1. Mission of this repo

`Cursor-Governance` is the single source of truth for L9/Quantum-L9 agent
governance: rules, skills, slash commands, learning corpus, and the automation
that wires all of it into every coding workspace.

This repo owns:

- the governance content itself (`rules/`, `skills/`, `commands/`, `learning/`)
- the symlink/wiring contract (`CANONICAL_LAW.md`)
- the session activation hooks (`ops/hooks/`)
- the Graphiti memory client and activation runbooks (`ops/graphiti/`)

This repo does **not** own:

- repo-specific rules (those live in the consumer repo's `.cursor/rules/`)
- app/product code of any kind

---

## 2. Activation — how a session boots L9 governance

**There is exactly one activation mechanism, and it is automatic.**

### 2.1 SessionStart (every session, no action needed)

`ops/hooks/session_start_bootstrap.sh` is installed as a real file at
`~/.cursor/hooks/session-start-bootstrap.sh` and registered in
`~/.cursor/hooks.json` under `sessionStart` (**60s** timeout). It:

1. Foreground-runs `governance_activate_fresh.sh` **before** resolving the
   SSOT. Tip authority is GitHub `origin/main` (ff-only when safe, else
   shallow clone + atomic swap). Prefers
   `$HOME/.cursor-governance/ops/scripts/governance_activate_fresh.sh`, then
   the `~/.cursor/hooks/governance-activate-fresh.sh` sidecar; chicken-egg
   minimal clone if both are missing. Parses the STATUS line
   (`action` / `sha` / `remote_sha` / `detail`).
   `governance_sync.sh` is **on-demand** bidirectional reconcile only — it is
   **not** the sessionStart tip-activation step.
2. Backgrounds `claude_projection.py --root "$GC" --workspace "$REPO" --quiet`
   — the one Claude projection engine (skills, commands, rules mount, settings
   triad, hooks, and declarative plugin state from
   `environment/agents/adapters/claude-code/plugins.desired.json`;
   `setup_claude_code_plugins.sh` runs only as the engine's fallback — see
   `environment/plugins/README.md`).
3. Auto-wires consumer `.cursor-commands`, `.cursor/plans` → `~/.cursor/plans`,
   and the `l9-governance` plugin when missing. SSOT must **not** self-alias
   `.cursor-commands`.
4. Backgrounds `install_ide_profile.sh --quiet` (extensions machine-wide;
   managed-key merge into `.vscode/settings.json`).
5. Loads Graphiti env, ensures the SSH tunnel, health-checks. Does **not**
   scaffold or excerpt `memory-bank/`. Resume SSOT is Graphiti (`inject` /
   PICKUP / hydration). See `ops/graphiti/MEMORY_BANK_POLICY.md`.
6. Runs `check_governance_wiring.sh` (PASS/FAIL, including tip freshness
   `HEAD == origin/main`).
7. Delegates to `ops/hooks/session_start_memory_orchestrator.sh` (code-graph
   on PlasticOS repos + Graphiti `inject "session start"` with
   `hydrate_stats`).
8. Emits sectioned markdown `additional_context` (Governance / Runtime /
   Graphiti hydrate / Code-graph / Plan audit) via COMBINED env. Exit 0 always.

Do not recreate a YAML `start-session.yaml` “protocol.” The `.sh` hook is the
canonical activation mechanism.

### 2.1.1 Worktree create ⇒ wire (not sessionStart)

`sessionStart` fires when Cursor opens a session in a folder. It does **not**
fire when an agent runs `git worktree add`. After creating a worktree:

```bash
# Default is PR_STACK=auto (Makefile): start on the unique open-PR tip.
# Opt out (origin/main): PR_STACK=  before the launcher.
bash "$HOME/.cursor-governance/ops/scripts/agent_worktree_start.sh" --agent-id <id> --task-id <task>
# Existing worktree (already created):
bash "$HOME/.cursor-governance/ops/scripts/ensure_workspace_wired.sh" /path/to/wt
```

`make pr` heals missing links under its repo-write lock, then fail-closes on
`check_governance_wiring.sh`. A later branch on the same folder does not need
another wire. Do not treat `/start-session` as a per-branch ritual.

### 2.2 Manual / on-demand commands

```bash
make -C "$HOME/.cursor-governance" start WS="$(pwd)"
```

Consumer repos may add a two-line delegating `start` target so plain
`make start` works from inside the repo.

**Invariant:** `make pr` / PR pre-commit scan **changed files only** (vs
`PR_BASE`, default `origin/main`); full-corpus scans are nightly CI
(`make pr-full` / `make precommit` for intentional local full runs).

```bash
make -C "$HOME/.cursor-governance" pr WS="$(pwd)"
make -C "$HOME/.cursor-governance" pr-security WS="$(pwd)"
```

There is **no** `tools/l9_repo/` tree and **no** `Makefile.template` in this
repo. Consumers that only need governance `pr` use this delegate — they do
**not** copy this repo’s fat Makefile:

```makefile
pr:
	$(MAKE) -C "$(HOME)/.cursor-governance" pr WS="$(CURDIR)"
```

Piecewise repair (run from the consumer workspace unless noted):

```bash
bash "$HOME/.cursor-governance/ops/scripts/governance_activate_fresh.sh"
bash "$HOME/.cursor-governance/ops/scripts/governance_sync.sh"
bash "$HOME/.cursor-governance/ops/scripts/check_governance_wiring.sh" "$(pwd)"
bash "$HOME/.cursor-governance/ops/scripts/setup_workspace_symlinks.sh"
bash "$HOME/.cursor-governance/ops/scripts/validate_governance_symlinks.sh"
"$HOME/.cursor-governance/.venv/bin/python" \
  "$HOME/.cursor-governance/ops/scripts/claude_projection.py" \
  --root "$HOME/.cursor-governance" --workspace "$(pwd)" --summary
bash "$HOME/.cursor-governance/ops/scripts/install_ide_profile.sh" "$(pwd)"
"$HOME/.cursor-governance/.venv/bin/python" \
  "$HOME/.cursor-governance/ops/graphiti/graphiti_memory_client.py" health
```

`setup_workspace_symlinks.sh` and `validate_governance_symlinks.sh` resolve
the workspace as `$(pwd)`. Running them from inside `~/.cursor-governance`
must **not** create a `.cursor-commands` self-alias (setup removes it).
Prefer wiring consumers, not the SSOT clone.

### 2.3 Session-end backup

This clone reconciles with `origin/main` on demand via `governance_sync.sh`
(ff-only pull, then push via `backup_to_github.sh`) and pushes again at
session end (`backup_to_github.sh` via the `sessionEnd` hook). Both directions
are commit-preserving. The session-end push is gated by
`ops/scripts/backup_gate.sh`. If a backup you expected did not happen, read
`backup.log`. Do not weaken the gate; run `make backup` or set
`GOVERNANCE_BACKUP_FORCE=1`.

---

## 3. Autonomy and merge

SSOT: `ops/autonomy/surface_profile.yaml` (CANONICAL_LAW §6.1 / §6.2).

Shared autonomy brain is `ops/autonomy/` (Cursor-primary). Provider-neutral
bounded-concurrency runtime is
`environment/program-execution/peer_execution/autonomy/`. No provider owns a
scheduler. Do not rewrite the Python scheduler from Cursor.

Claude Code gold-standard pack: `environment/agents/adapters/claude-code/`.
`environment/claude-code/` does **not** exist. The pack has **no** `autonomy/`
subdirectory. Cloud Web/Mobile memory uses HTTPS Graphiti
(`GRAPHITI_MCP_URL=https://memory.quantumaipartners.com/graphiti/mcp`);
see ADR-0006 + ADR-0007.

**Cursor** scoped-commits locally without asking (pathspecs; rule 49).
Ask-first applies to push / `make pr` only.
Adapter surfaces (`claude-code`, `codex`, `gemini`, `manus`) with
`L9_AUTONOMY_ENABLED=true` may scoped-commit locally without per-action ask.
They still publish only via `make pr`. Install settings:
`make claude-settings WS="$(pwd)"`.

### 3.1 L4 local autonomy (default ON)

`L9_L4_LOCAL_AUTONOMY=1`. Local commits only through program/contract
execution — **no mid-execution push**. When finished locally, run
`kernels/Recursive Alignment.md` then `kernels/Validate & Repair.md`, then
`make improve IMPROVE_RECORD=1` (or `l4-begin` / `l4-record-kernels` /
`l4-authorize`). An L4 release receipt does **not** authorize merge.

Enforcement: `ops/autonomy/local_execution_gate.py` (Claude PreToolUse +
Cursor `beforeShellExecution`) and `open_pr_after_gate.sh`. Status:
`make l4-status`.

### 3.2 Merge authority (resolved)

Launching a program or clicking Build is **not** merge authorization.

- Campaigns and `make pr` end **green + merge-ready**. They do **not** merge.
- Invoking **`/l9-pr-remediation` (Converge)** **is** merge authorization for
  **all open PRs**. Write
  `"$HOME/.cursor-governance/.venv/bin/python" ops/autonomy/authorize_merge.py --repo <owner/name> --all-open`,
  converge each PR, then merge oldest first, stack-safe.
- `/pr` is Diagnose-only (no merge).
- `L9_MERGE_AUTHORIZED=<reason>` is the human breakglass for ordinary merge.
- Force-push, hard-reset, and `--admin` stay denied.
- Squash/rebase is denied when the head branch is the base of an open PR
  (`ops/autonomy/merge_gate.py`). Land children bottom-up first, retarget
  them, or merge the parent with `--merge`. Breakglass:
  `L9_STACK_CHECK_BYPASS=<reason>`.
- After a parent is squash-merged, never merge `main` into the child. Use
  `git rebase --onto origin/main <old-parent-tip> <child>`.
- Do not split mixed work into a parent that deletes and a child that
  restores. Cut sibling branches from the pre-mix base instead.

For parallel non-dependent Tasks and background PR-poll, use `/autonomy` and
skill `l9-bounded-autonomy` (explicit-only). Authority is a **campaign
authorization packet**.

### 3.3 Campaigns

One integration branch per campaign (`campaign/<campaign_id>`). Set
`PR_BASE=origin/campaign/<campaign_id>`. Do **not** open campaign PRs against
`main`. Do **not** mix campaign work onto other feature branches. Branch map:
`environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml`.
Publish with `PR_REMEDIATE=0 make pr`.

---

## 4. Publish path (capability graph)

Makefile is a capability graph.

| Kind | Verbs |
|---|---|
| **PUBLIC** | `improve`, `pr-check`, `pr` |
| **INTERNAL** | `pr-preflight`, `precommit`, `precommit-repo` |

This repo does **not** use a git commit hook. Do not run `pre-commit install`.

1. `make improve` composes L4 wrappers. Apply the two kernels, commit
   revisions, then `make improve IMPROVE_RECORD=1`.
2. `make pr-check` is quality only (changed-files pre-commit + locked ruff /
   security / pytest). No L4. Empty changeset vs `PR_BASE` is PASS. A PASS
   writes `.l9/pr/gate-receipt.json`. The same HEAD + worktree + `PR_BASE` is
   not re-gated.
3. Preferred path to GitHub = **`make pr`** after L4 release — the only route
   that runs the checkers. Mechanically denied at every phase: `make push`,
   MCP `create_pull_request` / `push_files`. Raw `git push` / `gh pr create` /
   `gh pr edit` are **off doctrine but not blocked**: git and gh are exempt
   from the workflow plane and answer to `ops/autonomy/git_guardrails.py`,
   which denies by effect (CANONICAL_LAW §6.2.4). Do not expect a denial
   message to stop you — prefer `make pr` because it gates, not because the
   alternative errors. `make pr` / `PR` / `Pr` / `pR` are equivalent.
4. Failure loop: diagnose → fix → (`make improve` if kernels apply) →
   `make pr-check` → `make pr` **once**. Do not run a second full gate on an
   unchanged tree.
5. `make pr` runs INTERNAL `pr-preflight`, then `pr-check` (receipt skip if
   unchanged), then `open_pr_after_gate.sh`.

`make pr` auto-heals derived artifacts via
`ops/scripts/sync_generated_artifacts.py` (WARN to stage, not a hard fail).

**`PR_REMEDIATE`:** Makefile default is `1` (after open, emit
`L9_AGENT_REQUIRED` so the agent may spawn `l9-pr-remediation`).
`open_pr_after_gate.sh` itself defaults to `0` if the env is unset.
Campaign and L4 authorize-release publish **MUST** pass
`PR_REMEDIATE=0 make pr`. Spawn remediation only when `PR_REMEDIATE=1` or
the user invokes `/l9-pr-remediation`. Cap in the skill pack is **3**
(`skills/l9-pr-remediation`). `surface_profile.yaml` lists `max_cycles: 5`
— follow the skill pack until that key is aligned.

Handoff: `.l9/pr/pr-remediation-handoff.json`. Live rule:
`rules/48-make-pr-remediation.mdc`.

Do not open or push if `make pr` / `make pr-check` fails.

CI Lint is `uv run ruff`, not the pre-commit CLI. Pin lockstep:
`.pre-commit-config.yaml` ruff `rev` matches `requirements.txt`.

### 4.1 PR overlap

SSOT: `rules/53-pr-overlap-guardrail.mdc`; policy under
`pr_stacking.pr_overlap` in `ops/autonomy/surface_profile.yaml`.

`make pr` runs `ops/scripts/pr_overlap_check.py` between the L4 release
check and `git push`. Default `PR_OVERLAP=block`. Generated artifacts
(`GENERATED_PATH_PREFIXES` in `ops/scripts/sync_generated_artifacts.py`)
are exempt and merge via `merge=l9-generated`.

Overlap remedy: commit into the same-agent open PR, else wait, else
renegotiate scope. `PR_STACK=auto` is the default at start and at
`make pr` — not an opt-in exception. Empty `PR_STACK` keeps
`origin/main`. Fail-open on missing `gh` telemetry; fail-closed on a
detected non-generated textual conflict.

`agent_worktree_start.sh` bases the worktree on the unique open-PR chain
tip (implied `L9_TASK_BASE_AUTHORIZED` for that tip only). Do not invent
an `origin/main` fork and restack at `make pr`. Sibling open-PR chains
still fail closed.

Opt out with `PR_STACK= make pr` to publish against `main`. A stack
parent must merge with `--merge`, or children must land first — squash
of a parent silently drops the child.

After any merge touching generated paths, or while
`.l9/pr/regen-required.txt` is non-empty, run
`"$HOME/.cursor-governance/.venv/bin/python" ops/scripts/sync_generated_artifacts.py --force`,
stage, and commit before opening or updating a PR.

---

## 5. Interpreter

Makefile recipes MUST call `$(PYTHON)` / `$(RUFF)` / `$(MYPY)` —
`$(CURDIR)/.venv/bin/{python,ruff,mypy}` from `pyproject.toml` + `uv.lock`
(`make venv` → `uv sync --locked --extra dev`). macOS `/usr/bin/make` is
GNU Make 3.81 and does **not** export `export PATH :=` into recipe shells.

`make gov-python` is an auto-prereq of every goal except `help` / `venv`.
It runs `ops/scripts/ensure_gov_python.sh` and fail-closes unless
`sys.prefix` is `.venv` and `yaml`, `pydantic`, `jsonschema`, `structlog`,
`cryptography`, and `langgraph` import.

Manual Graphiti / secrets / L4 / `authorize_merge.py` /
`sync_generated_artifacts.py` / `port_aws_to_infisical.py` MUST use
`"$HOME/.cursor-governance/.venv/bin/python"` (or a `make` target).
`ModuleNotFoundError: No module named 'yaml'` means the wrong interpreter.

Exception (known): three `replay_campaign.py` recipes in the Makefile still
call bare `python3`. Do not copy that pattern.

Do not `uv pip install` past the lockfile for the default toolchain.

---

## 6. Toolchain pins (local `make pr` / pre-commit)

SSOT: [`requirements.txt`](requirements.txt) + `uv.lock`. Keep
`pyproject.toml` `[project.optional-dependencies] dev` and
`.pre-commit-config.yaml` ruff `rev` in lockstep.

Live authority in `requirements.txt`: ruff / mypy / pytest match
**l9-ci-core** `install-consumer-ci`. Other analysis tools follow l9-ci-sdk
when it pins them. Core owns gitleaks / bandit / pip-audit (sdk omits).

| Tool | Version | Install | Source |
|---|---|---|---|
| ruff | `0.16.1` | `make venv` | `requirements.txt`; pre-commit `rev: v0.16.1` |
| mypy | `2.3.0` | same | `requirements.txt` |
| pytest | `9.1.1` | same | `requirements.txt` |
| pytest-cov | `7.1.0` | same | `requirements.txt` |
| types-PyYAML | `6.0.12.20260724` | same | `requirements.txt` |
| bandit | `1.9.4` | same / `uvx` | `requirements.txt` |
| pip-audit | `2.10.1` | same / `uvx` | `requirements.txt` |
| gitleaks | `8.24.3` | `brew install gitleaks` | comment in `requirements.txt` |
| semgrep | `>=1.100.0,<2.0.0` | brew / pip / `uvx` | sdk SemgrepVersionPolicy |
| pre-commit | latest stable | pipx / pip / brew | framework only |
| uv | `>=0.8.0` | https://docs.astral.sh/uv/ | `[tool.uv] required-version` |

```bash
make -C "$HOME/.cursor-governance" venv
brew install gitleaks
```

**Not required for `make pr`:** `SEMGREP_APP_TOKEN` / `semgrep login`,
`SONAR_TOKEN`.

---

## 7. Graphiti

Graphiti memory is activated. C1 `graphiti-mcp` is pinned to
`zepai/knowledge-graph-mcp:1.0.2-graphiti-0.28.2-standalone` per
`ops/graphiti/docker-compose.yml`. Client tool names:
`add_memory`, `search_memory_facts`, `group_ids` (list).

Expect `"graphiti: healthy"` / a successful `tools/list`. If you see
`"MCP tools degraded"`, check the deployed image on C1
(`docker inspect graphiti-mcp-cursor --format '{{.Config.Image}}'` should say
`zepai/knowledge-graph-mcp`, not `zepai/graphiti`).

Health:

```bash
"$HOME/.cursor-governance/.venv/bin/python" \
  "$HOME/.cursor-governance/ops/graphiti/graphiti_memory_client.py" health
```

Residual `memory-bank/` trees are archival residue; wiring checks WARN if
present and PASS when absent. Agents must not recreate them.

On chat X-out (`sessionEnd`), archive user/assistant text + timestamps to S3
`l9-chat-transcripts-020125249784`
(`python -m ops.graphiti.hydration.archive_transcript` via the locked
interpreter). See `ops/scripts/RETIRED_export_chats_and_learning_processor.md`.

---

## 8. Secrets

**AWS name-inventory SSOT:** `ops/secrets/openclaw-igorbot.registry.yaml`
(`openclaw-igorbot/*`, `us-east-1`). `make secrets-sync` /
`make secrets-check REF='…'`. Skill `l9-aws-secrets`.

**Infisical (long-term values):** project **Cursor-Governance**
(`slug: cursor-governance`, env `prod`, path `/`). Inventory:
`ops/secrets/infisical-cursor-governance.yaml`. Hydrate from
`openclaw-igorbot/infisical-cursor-governance`. Re-port:
`"$HOME/.cursor-governance/.venv/bin/python" ops/secrets/port_aws_to_infisical.py`.

Secret **values** never in git/logs/receipts/chat. UI operator:
`ops/ui-operator/` / skill `l9-ui-operator` (explicit-only);
`make ui-operator-sync`.

**GitHub authority (`CANONICAL_LAW.md` §14):** resolve
`openclaw-igorbot/github#token` for `gh`/API work. Do **not** ask the human
to operate `github.com` UI when that PAT can complete the outcome. Do **not**
provision a second GitHub PAT in AWS while this ref works.

---

## 9. Source-of-truth files

- `CANONICAL_LAW.md` — symlink law, memory layer, anti-patterns (authoritative)
- `README.md` — directory structure and key-file index
- `ops/hooks/session_start_bootstrap.sh` — activation entry point (§2.1)
- `ops/scripts/resolve_governance_paths.sh` — path resolution (GitHub clone
  only, no Dropbox fallback)
- `ORG_INVARIANTS.yaml` — canonical Quantum-L9 org policy
- `ops/autonomy/surface_profile.yaml` — autonomy / L4 / campaign / overlap
- [`requirements.txt`](requirements.txt) — toolchain pins
- `ARCHITECTURE.md` — this-repo map (index; does not outrank this file or `CANONICAL_LAW.md`)
- `INVARIANTS.md` — this-repo invariant index (`ORG_INVARIANTS.yaml` remains the machine org-policy SSOT)

Agents must keep code and these docs aligned — see `TODO.md` for known drift
not yet reconciled.

---

## 10. Symlink law (summary — `CANONICAL_LAW.md` §1–3 is authoritative)

| Workspace path | Target |
|---|---|
| `.cursor-commands` | `~/.cursor-governance/` (consumers only; SSOT must not self-alias) |
| `.cursor/governance/CANONICAL_LAW.md` | file symlink to the law file only |
| `.cursor/governance/` | local directory, **never** a symlink to the governance root |
| `.cursor/plans` | `~/.cursor/plans` |
| `~/.cursor/plugins/local/l9-governance` | governance root (plugin discovery) |

Do **not** create `~/.cursor/{skills,commands,rules}` whole-directory
symlinks — `setup_workspace_symlinks.sh` removes those pre-4.0.0 artifacts.
Cursor discovers `rules/`, `skills/`, `commands/` under the plugin root.

Forbidden: a second governance tree in any repo, `.cursor/commands` or
`.cursor/skills` duplicating `.cursor-commands/*`, hard-reset/force-push of
this clone.

**Cursor-primary ownership (`CANONICAL_LAW.md` §2.1):** build shared capability
in Cursor-primary / `ops/` first; wrap outward for Claude Code and other
adapters. Never implement a shared brain under an adapter tree and have
Cursor import it.

---

## 11. Workspace kinds

`ops/scripts/lib/workspace_kind.sh`: `ssot` | `ssot_checkout` | `consumer`
(identity files, not a `$HOME/.l9/gov-worktrees/` prefix).

1. `ssot` = live `$HOME/.cursor-governance`. No `.cursor-commands` self-alias.
2. `ssot_checkout` = worktree or second clone of this repo. `make pr` /
   `symlinks-check` must not require consumer IDE wiring.
3. `consumer` = every other governed repo. Unchanged.

Do not “fix” a gov worktree by running `setup_workspace_symlinks.sh` just
to pass `make pr`.

---

## 12. Change policy

### 12.1 Allowed

Bug fixes, dangling-reference repair, test/doc additions, new skills via
`l9-skill-compiler` → `l9-wire-skill-into-repo`.

### 12.2 High-risk — extreme care

Changes to `CANONICAL_LAW.md`, `resolve_governance_paths.sh`,
`backup_to_github.sh`, `ops/hooks/session_start_bootstrap.sh`, or anything in
`ops/scripts/_archived/` (archived = intentionally retired, not missing —
verify the archival rationale in git history before restoring anything).

`pyproject.toml` is a **protected file** (`ORG_INVARIANTS.yaml`
`protected_paths` + CODEOWNERS): **append only — never overwrite existing
keys or lines.** Put additive pytest collection controls in root
`conftest.py` instead of rewriting `[tool.pytest.ini_options] addopts`.

### 12.3 Forbidden

- Reintroducing Dropbox as an SSOT fallback in any resolver script
- Owning shared cross-surface capability under a dependent adapter and wrapping
  Cursor to consume it (violates `CANONICAL_LAW.md` §2.1)
- Restoring archived pre-Graphiti daemons without confirming they're not
  superseded (`git log` the archiving commit first)
- A new YAML/manual “protocol” file duplicating the `.sh` hook’s job

Before restoring anything from `ops/scripts/_archived/`, run
`git log --oneline -- ops/scripts/_archived/<file>` and read the archiving
commit. Prefer fixing the stale checker over restoring the retired artifact.

### 12.4 KERNEL pack landing branch

Do **not** ask whether to land a KERNEL pack, PE overlay, or similar governed
architecture change on the current feature branch vs a new branch. Default:
new branch from `origin/main` (ff-only tip); do not mix unrelated WIP. Rule:
`rules/46-kernel-pack-new-branch.mdc`.

---

<!-- PROGRAM_EXECUTION_ADAPTER_LAYER_V1:AGENTS -->

## 13. Program Execution adapter layer

The reusable subsystem lives at `environment/program-execution/`. Do not copy
its core schemas, root `autonomy/`, the Claude bounded-autonomy scheduler,
the agent registry, or the Graphiti client into an adapter.

Program Execution tasks use the Program Execution Controller lease as the
sole authoritative work claim. They must not acquire a competing Graphiti
task claim. A Graphiti projection is observability only.

```bash
make program-execution-core-validate
make program-execution-adapters
make program-execution-conformance
make program-execution-probe
make pr
```

---

<!-- ROOT_FILE_APPEND_ONLY_PROTECTION_V1 -->

## 14. Repository-root files are append-only

Every file at the repository root is protected. Incoming changes may **add**
content freely, but may **not delete or overwrite** existing content in a
protected root file without both:

1. an `ALLOW-ROOT-DELETION: <path> — <reason with proof of necessity>` line
   in a commit message, and
2. CODEOWNERS approval from the repository owner.

Authoritative list: `ops/config/root-file-protection.json`.

- **additive_only** — deletions/overwrites fail the gate without the marker
- **managed** — edited freely with owner review; no marker
- **regenerable** — rewritten wholesale by tooling

A new root file must be registered with a tier. Enforcement:
`.github/workflows/root-file-protection.yml` →
`ops/scripts/validate_root_file_protection.py`. Removing or weakening the
gate is itself a protected-path change (`ORG_INVARIANTS.yaml`
`protected_paths`).

This file is `additive_only`. A whole-file fold (this revision) is authorized
only when the commit includes `ALLOW-ROOT-DELETION: AGENTS.md — …`.

<!-- PROTECTED_ROOT_PR_TEMPLATE_V1 -->

PRs that touch any `additive_only` root file (`Makefile`, `AGENTS.md`,
`CANONICAL_LAW.md`, `pyproject.toml`, `requirements.txt`, `conftest.py`,
`.pre-commit-config.yaml`, `.gitleaks.toml`, `.mcp.json`, `CODEOWNERS`,
`LICENSE`, `SECURITY.md`, `ORG_INVARIANTS.yaml`) **MUST** use
`.github/PULL_REQUEST_TEMPLATE/protected-root.md`. The body must contain the
stamp `<!-- L9_PROTECTED_ROOT_PR -->`. `make pr` injects that template.
The Root-file append-only gate fails CI without the stamp. Prefer
append-only so `ALLOW-ROOT-DELETION` is unnecessary; a rewrite still needs
that marker in a commit message.

Review threads (GitHub Code Quality, Copilot, Codex, humans) stay in scope
for `/l9-pr-remediation`. Inspect each proposed fix against current source
and apply it when justified. A finding whose **only** path is under `WIP/**`
cannot fail CI and is not a merge-blocking code defect.

---

## 15. WIP corpus on main

`WIP/` is a **dated tracked corpus on `main`**. Prefer `WIP/<M-D-YY>/<topic>/`.
Named series (`WIP/CG/`) stay and are inventoried.

Agents **may** read/write WIP for hygiene, filing loose root notes, and
high-evidence prune (`make wip-hygiene` / `ops/scripts/wip_corpus.py`).
Auto-prune only when a WIP file’s sha256 matches a tracked **non-WIP** path,
or inventory has an explicit `landed:` marker. Receipts:
`WIP/_receipts/`.

Do **not** park WIP under `/tmp` or `.l9/scratch-hold/`. Stage with pathspecs
only (rule 49). `WIP/Legal Defense/` and credential globs stay untracked.
`TODO.md` remains the agent task queue. `l9-git-work-preserve` inventories
git refs/stashes and never auto-deletes branches.

---

## 16. SessionStart Plan audit

Bootstrap `additional_context` includes `### Plan audit`, produced by
`skills/l9-plan-audit/scripts/audit_plans.py` (fail-open, ~2s budget).
Scans machine-global Cursor plans for **unbuilt** plans with mtime in the
last **7 days**. Findings are **display-only** — do not auto-Build.
On-demand: `/plan-audit`.

---

## 17. Stack-safe merge + automatic hygiene

Local residue is cleaned at `sessionEnd` by `ops/scripts/repo_hygiene.py`
(see `ops/scripts/REPO_HYGIENE.md`). Spent branches, spent worktrees, and
stale stashes go without being asked; every delete is preceded by a
`refs/l9/preserved/` ref. Dirty worktrees and untracked files are never
touched, only reported. Do not ask the human whether there are untracked
files — run the report.

A branch name is never reused after its PR merges
(`reused_after_merge` — hygiene refuses to delete it).

---

## 18. pre-commit “files were modified by this hook”

That message names a **window**, not a writer. `symlinks-check` has the
widest window and is repo-read-only. Do **not** audit the named hook first:

```bash
bash ops/scripts/attribute_tree_writers.sh "$(pwd)" <status-before> <precommit-log>
cat .l9/pr/gate-dirtiness.json
```

`make pr` separates a real `- exit code:` FAIL from a modified tree
(classify → attribute → quiesce → retry once). Every hook is
`read_only` or `writer` in `ops/config/precommit-hook-contract.json`.
Automated writers serialize behind `ops/scripts/lib/repo_write_lock.sh`.
Background: `learning/failures/precommit-hook-attribution.md`.

---

## 19. Guidance for AI coding agents

- Before restoring anything from `ops/scripts/_archived/`, read the
  archiving commit. “Nothing references it” is not sufficient to restore
  or to delete permanently.
- Prefer fixing the stale artifact over restoring the retired one.
- Never hand-edit files in a way that assumes a different sync model than
  ff-only pull + rebase-and-abort push.
- If `install_ide_profile` dirties only the generated formatter block,
  restore `AGENTS.md` from HEAD unless `environment/ide/policy.json` changed.

---

## 20. Final principle

This repo is the governance boundary for every L9/Quantum-L9 coding workspace.
Activation must stay boring and automatic — one hook, one clone, one symlink
per consumer repo. Optimize for that staying true; do not add a second
activation path, however convenient it seems in the moment.

<!-- BEGIN L9 FORMATTER OWNERSHIP (generated — do not edit) -->

## Formatter ownership

Workspace class: `biome_default` — Default for every governed workspace: Biome owns JS/TS/JSON, VS Code JSON language features owns JSONC (the Biome extension cannot format jsonc), Ruff owns Python, Prettier owns Markdown (format-on-save off so governance docs do not churn).

Exactly one formatter owns each language. Do not reformat a file with a tool other than its owner, and do not add config for a competing formatter: the result is a diff that churns on every save.

| Languages | Owner | Note |
|---|---|---|
| `javascript`, `javascriptreact`, `typescript`, `typescriptreact`, `json` | **biome** | bound by the governed IDE profile |
| `jsonc` | **vscode-json** | bound by the governed IDE profile |
| `python` | **ruff** | bound by the governed IDE profile |
| `markdown` | **prettier** | bound by the governed IDE profile |

Generated from `environment/ide/policy.json` in the governance clone by `ops/scripts/adapters/agentdocs.sh`. Edit the policy, not this block.

<!-- END L9 FORMATTER OWNERSHIP -->

<!-- CURSOR_PLANS_REPO_STORE_V1 -->
## Cursor plans store (2026-08-20) — supersedes “not governance SSOT” plans wording

Authoritative corrections (do not treat older “convenience / not SSOT” bullets
as the live store):

1. Machine-global Cursor plans are tracked at `docs/plans/` in this repository.
2. `~/.cursor/plans` is a symlink to that directory. Workspace `.cursor/plans`
   still points at `~/.cursor/plans` and therefore writes into `docs/plans/`.
3. First-run stamp: `$HOME/.cursor/l9-plans-store` (one absolute path). Prefer
   the `ssot` / `ssot_checkout` you ran setup from so an `activate_fresh` swap
   of `$HOME/.cursor-governance` cannot drop uncommitted plans.
4. Do not `mkdir -p ~/.cursor/plans` as a real directory. Use
   `ops/scripts/lib/cursor_plans_store.sh` → `ensure_machine_cursor_plans_store`.

<!-- MAKE_PR_CASE_INSENSITIVE_V1 -->
## `make pr` capitalization (2026-08-20)

`make pr` / `make PR` / `make Pr` / `make pR` all run the same gate.

<!-- PRECOMMIT_REPO_OWNS_RUFF_V1 -->
## `make precommit-repo` before `make pr` (2026-08-21)

After every local commit, run `make precommit-repo` (changed-file hooks +
locked `ruff check` / `ruff format --check`). If hooks rewrite files, commit
the rewrite and re-run. Do not auto-stage. Then `PR_REMEDIATE=0 make pr`.

`make pr-check` still runs pytest, wiring, and `run_pr_security.sh`. It does
**not** run a second ruff pass. There is no git commit hook — do not run
`pre-commit install`. Local autofix is `precommit-repo`. `.github/workflows/lint-autofix.yml`
is a post-merge janitor on `main` only.

<!-- L9_PLAN_SIMPLE_V1 -->
## Two plan skills (2026-08-21)

Ordinary Cursor Plan mode / Build uses **`l9-plan-simple`** (`/l9-plan-simple`).
It fills the same first-class template
(`environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`)
and executes with the **Build** button on the current checkout. It does **not**
run `make campaign`, admit a Program Lock, or write `Lock: origin/main = <sha>`.

**`l9-plan`** (`/l9-plan`) stays the PE/campaign planner: same template **and**
the Program Execution execute path. Use it only when the user asks for
`/l9-plan`, `make campaign`, Program Lock, or PE+autonomy.

<!-- PR_GATE_VELOCITY_V1 -->
## PR-gate velocity vs `make pr-full` (2026-08-22)

`make pr` / `make pr-check` is the **velocity path**: changed-file pre-commit
hooks (filename + ruff) plus the landed scoped pytest selector
(`select_pr_pytest_paths.py` / `run_python_test_suites.py --changed-file`).
Corpus hooks (`repo-hygiene`, `legacy-doctrine-residue`, `rules-check`,
`skills-check`), residue / contract-surface / git-denial always-run, and the
full pytest catalog belong to `make pr-full` / `make precommit`
(nightly-adjacent).

Makefile `push` is `precommit-repo backup` (changed files), not `--all-files`.
sessionEnd (`backup_to_github.sh`) is unchanged and is not this path.

capability-contract runs on `make pr` only when the change set matches
`^(ops/secrets/|environment/agents/)`. Workflow pins run only when
`.github/workflows/` or `ops/scripts/validate_workflow_action_pins.py`
changed.

<!-- PLAN_KERNEL_AUTO_PASS_V1 -->
## Plan kernel pass (2026-08-21)

Hooks plus a hashed receipt force Improve then Validate & Repair on **one**
Cursor `.plan.md` in the machine plans store (`realpath($HOME/.cursor/plans)`).

1. `postToolUse` writes `$WS/.l9/plan/kernel-pass-required.json` when a store
   `.plan.md` fails `skills/l9-plan/scripts/validate_plan_kernel_receipt.py`.
2. `beforeSubmitPrompt` (existing skill router) prepends the inject block.
3. `beforeShellExecution` denies `make campaign` / `run_campaign.py` when that
   latch or an argv `.plan.md` still FAILs. `pec.py` and `make pr-check` stay
   allowed.
4. SessionStart plan audit may flag `kernel_unfired` (display-only).
5. Canonical sha is SHA-256 of the file after every `body_sha256` scalar is
   replaced with 64 zeros. Empty `deltas` is FAIL. Do not create a second plan.

<!-- ROOT_DOC_AUTHORITY_MAP_V1 -->
## Root-doc authority map (2026-08-21)

Do **not** fold this file into a thin pointer. `AGENTS.md` remains the
operating-instruction SSOT. This section is additive only.

| File | Role |
|---|---|
| `CLAUDE.md` | Load pointer — authority chain only; no doctrine dump |
| `AGENTS.md` | Operating-instruction SSOT (this file). Additive-only. Do not fold. |
| `README.md` | Index pointing at `CANONICAL_LAW.md` and this file |
| `CANONICAL_LAW.md` | Constitution. Not edited by the root-docs skill. |
| `skills/l9-*` | Task procedures. Cite kernels by path; do not wrap kernels. |

When refreshing root docs, use skill `l9-update-agent-docs`. That skill **reads**
`kernels/Recursive Alignment.md` for the audit and must not embed or compress
the kernel. Do not invent root `ARCHITECTURE.md` or `INVARIANTS.md`. Generated
formatter-ownership blocks are companions owned by `environment/ide/policy.json`.

<!-- ROOT_DOC_VR_REPAIR_V1 -->
## Root-doc repair citation (2026-08-21)

When `l9-update-agent-docs` repairs a confirmed pointer defect, it **reads**
`kernels/Validate & Repair.md` by path. It must not embed or compress that
kernel. Repairs stay the smallest source-aligned edit; report only validation
that ran (Passed / Failed / Skipped / Unknown / NotApplicable).

<!-- L9_FF_REPO_SYNC_V1 -->
## `/ff` in-place catch-up (2026-08-22)

Catch a named Cursor-Governance clone up to `origin/main` **in place** via
`/ff` or `make ff` (`skills/l9-repo-sync/scripts/ff.sh`). Unique commits,
dirty tracked bytes, and untracked copies that main now tracks are **parked**
(never deleted). `.venv` stays. Do not run `governance_activate_fresh.sh` as
sync. `make sync` remains `governance_sync.sh` and is not `/ff`.

<!-- L9_SSOT_MACHINE_LOCAL_KEEP_V1 -->
## Machine-local keep across `/ff` and sessionStart (2026-08-26)

`/ff` and `governance_activate_fresh.sh` (sessionStart / `/start-session`)
must not clobber `.venv`, `.env.local`, `env.local`, `.env.*.local`, or
`.claude/settings.local.json`. A shallow-clone swap carries those paths
from the bak onto the new live tree before bak prune. `/ff` parks and
restores the same keep-list around `reset --keep` / checkout. Values are
never printed. Lib: `ops/scripts/lib/ssot_machine_local_keep.sh`.

<!-- L9_CURSOR_AUTO_COMMIT_V1 -->
## Cursor local commits (2026-08-22)

Agents **must** scoped-commit work they authored this session without asking.
Ask only before push / `make pr` / other remote mutation. Rule:
`rules/99-no-auto-commit.mdc`.

<!-- L9_CURSOR_COMMIT_BEFORE_STOP_V1 -->
## Commit before you stop (2026-08-27)

`99-no-auto-commit.mdc` is **always on**. The filename means **do not auto-push**,
not leave the tree dirty. After each authored chunk, scoped-commit on **this**
branch (pathspecs; rule 49). Before you tell the user coding work is done,
`git status` must show **no unique dirty files you authored**. Asking “should I
commit?” is a rule failure. Cursor User Rules that say “only commit when asked”
are overruled here for authored work. Push / `make pr` stay ask-first.

<!-- L9_AUDIT_PLANS_V1 -->
## Plans-store audit slash (2026-08-23)

On-demand shelf audit/organize is **`/l9-audit-plans`**
(`commands/l9-audit-plans.md`). Root stays current unbuilt only;
`partially-built/`, `built/`, `backlog/`, and `archive/superseded/` hold the
rest. `/plan-audit` is a compatibility alias of that command.

Skill **`l9-plan-audit`** is still the sessionStart 7-day live-queue scanner
(§16). It does not move files. Do not treat it as `/l9-audit-plans`.

<!-- L9_PIPELINE_AUDIT_V1 -->
## `/l9-pipeline-audit` (2026-08-28)

`/plan-audit` is a compatibility alias of **`/l9-pipeline-audit`**
(`commands/l9-pipeline-audit.md`). That command classifies Cursor plans,
`WIP/`, and `environment/program-execution/campaigns/` with the same
component verdicts, then harvests through skill `l9-intelligence-harvest`.
Compiled packets emit as a new plan, `WIP/<M-D-YY>/<concern>/`, or a
campaign `HARVEST_INTENT.md`. Execute via `/gmp`. Do not `make campaign`.
`/l9-audit-plans` remains the plans-store shelf organizer. SessionStart
`l9-plan-audit` is unchanged (plans-only, display-only).

<!-- L9_SESSION_PIPELINE_AUDIT_V1 -->
## SessionStart pipeline audit (2026-08-28)

§16 heading `### Plan audit` is unchanged. The producer is now
`skills/l9-pipeline-audit/scripts/audit_pipeline.py --format session-start`
(`~4s` fail-open). The plans store is the tracked `docs/plans/` directory
reached by `.cursor/plans` → `~/.cursor/plans`. The same scan covers
`WIP/` (skip Legal Defense and secret globs) and
`environment/program-execution/campaigns/*/CAMPAIGN_SOURCE.yaml`
(gov-root fallback on consumers).

SessionStart may archive spent root plans (`built/` or `archive/superseded/`)
and inventory-`landed` WIP (`WIP/_archived/`), cap 8, skip when the
repo-write lock is held. Mixed harvestable donors stay. Campaign sources
are never moved. Do not auto-Build. Do not auto-harvest.

The report lists pending counts and exactly three next executions in order:
compiled packets first (`/gmp`), then README live-queue names, then live
campaigns, then other unbuilt plans. `possible-landed` WIP is leftover, not
an execute slot.

`l9-plan-audit` remains the plans-surface scanner called by that CLI.
`/l9-pipeline-audit` remains the on-demand harvest slash.

<!-- FF_SHELF_WIP_PLANS_V1 -->
## `/ff` shelves leftover WIP and plans (2026-08-28)

After `skills/l9-repo-sync/scripts/ff.sh` succeeds, leftover **untracked**
`WIP/` and `docs/plans/` are shelved onto a sibling branch
(`feat/ff-shelf-<stamp>`, pathspecs only). `ff.sh` stays push-off.
Untracked bytes must be **copied** into the new worktree — a fresh checkout
does not have them. L4 state is workspace-local, so `begin` /
`record-kernels` / `authorize-release` run in that worktree before publish.
Publishing is **ask-first**: `/ff` catches a clone up, it does not authorize
`PR_REMEDIATE=0 make pr`. Skip paths an open `feat/ff-shelf-*` PR already
carries so repeat runs do not re-shelve the same bytes.
Secret globs and `WIP/Legal Defense/` stay out. Dirty-preserve refs stay
until `l9-git-work-preserve` triage + prune-policy.

<!-- L9_PR_REMEDIATE_SPEED_V1 -->
## `/l9-pr-remediation` publish is not `make pr` (2026-08-28)

§3.2 merge authority is unchanged: invoking **`/l9-pr-remediation` (Converge)**
**is** merge authorization for all open PRs. Campaigns and `make pr` stay
no-merge.

Remediator **publish** is a different path from the ceremony:

- Local verify is `PR_BASE=origin/main make precommit-repo` (changed-file
  hooks plus locked ruff). No pytest. No conformance. CI owns those.
- Publish is `git push` of the already-open PR branch. Pathspecs only.
- Do not run `make pr` or `make pr-check` from this skill.
- Do not poll CI after push. Continue the next independent PR, then
  MERGE_TRAIN. If merge is blocked by required checks, record the blocker
  and finish.

`make pr` / `make pr-check` remain the campaign / feature ceremony. This
section does not rewrite §4.

<!-- L9_GENERATED_SNAPSHOT_SCOPE_V1 -->
## Generated snapshot scope (2026-08-28)

`pull_request` `governance-self-check` uses `sync_generated_artifacts.py
--changed-file` (add `--pe-manifest` only when a path starts with
`environment/program-execution/`). `push` to `main` keeps
`--force --pe-manifest --check`. lint-autofix is the only generated janitor
(cleanup PR; never push to protected `main`).

`stack_safe_merge.py` keeps a parent ref while an open child still bases on
it. After the last child retargets or lands, the parent ref may be deleted.

Doctrine clause owners — later PRs **append a named fragment**. They do not
rewrite `ops/autonomy/surface_profile.yaml` `session_start_block` or the
whole `ops/scripts/run_pr_gate.sh`:

- remediator publish: `skills/l9-pr-remediation` + this file `L9_PR_REMEDIATE_SPEED_V1`
- unscoped pytest deny: `ops/scripts/run_pr_gate.sh`
- kernel hook: `ops/hooks/plan-kernel-gate.py`

<!-- L9_CEREMONY_STACK_AND_HEAL_V1 -->
## Ceremony stack-tip and generated heal (2026-08-28)

`PR_STACK=auto` resolves the unique open-PR chain tip at **precommit-repo /
pr-preflight / pr-check start**, not only after the gate in
`open_pr_after_gate.sh`. Empty `PR_STACK=` keeps `PR_BASE` (usually
`origin/main`). Sibling chains still fail closed. Missing `gh` keeps
`origin/main` with a WARN (fail-open telemetry). An explicit `PR_BASE` other
than `origin/main` / `main` is never rewritten. `open_pr_after_gate.sh` reuses
the stack-base receipt so the opened PR targets the same parent the gate used.

`sync_generated_artifacts.py` and `claude_projection.py` (no `--check`) run in
the **serialized writer** wave. Tracked dirt after that heal is "commit the
rewrite, then re-run" — same as ruff. Reader-wave yaml / projection `--check`
do not share a wall-clock window with that writer.
Reader `files were modified` with no hook exit code is classified (generated
WARN / window-only continue), not a hard Error 1.

Cherry-pick / rebase of `merge=l9-generated` paths still keep ours; the writer
heal regenerates from live sources. Do not publish until that regen is
committed.

<!-- FF_SWITCH_TO_MAIN_V1 -->
## `/ff` switches to `main` (2026-08-28)

`skills/l9-repo-sync/scripts/ff.sh` step 0: if HEAD is not `main`, park dirty
tracked and untracked paths that `origin/main` already tracks, then `git switch`
to `main`. Agents must not `git switch` themselves. The feature branch ref
stays. Unique feature commits are not `l9/ff-preserve-*`. Identity after
catch-up is same gitdir and HEAD on `main`.

<!-- FF_CORPUS_KERNELS_V1 -->
## `/ff` owns WIP / plans / campaign kernels (2026-08-28)

Leftover untracked `WIP/`, `docs/plans/`, and
`environment/program-execution/campaigns/` get Improve, then Recursive
Alignment, then Validate & Repair **before** commit and **before**
`.pre-commit-config.yaml` hooks. Shelved `*.plan.md` write `kernel_pass` with
those three blocks in `ran_at` order.

`ops/autonomy/kernel_gate.py` skips those prefixes. A corpus-only changeset
skips the tree latch too. L4 on the shelf worktree is `begin` then
`authorize-release` only — not `record-kernels`. Mid-session plan inject does
not apply those kernels; `/ff` is the apply site. This fragment supersedes
the `record-kernels` sentence in `FF_SHELF_WIP_PLANS_V1`.

<!-- CURSOR_SESSIONSTART_NO_CLAUDE_CLOUD_V1 -->
## Cursor SessionStart does not score Claude cloud (2026-08-29)

`ops/hooks/session_start_bootstrap.sh` does not run `claude_projection.py`.
Claude Code SessionStart (`session_start_claude_governance.sh`) is a no-op
unless a Claude runtime marker is set (`CLAUDE_CODE_REMOTE=true`,
`CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`, or `CLAUDE_CODE_SESSION_ID`).
`.governance-build-lock` is local-only (gitignored); presence still skips
backup. This fragment supersedes §2.1 step 2 (Claude projection from Cursor
SessionStart) and the older “keep `.governance-build-lock` tracked” housekeeping
decision.
