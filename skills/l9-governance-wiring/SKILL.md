---
name: l9-governance-wiring
description: Workspace wiring, component wiring, confirm-wiring audit, governance checks, rules inventory, and GitHub SSOT backup
disable-model-invocation: true
---

---
name: wire
version: "12.3.0"
description: "TRIGGER ONLY — governance workspace wiring OR wire_executor.py for code components"
before_chain: rules
auto_chain: ynp
dag_executor: .cursor/workflows-synced/wire_executor.py
---

# /wire — Component Wiring (v12.3.0)

## THIS IS A TRIGGER ONLY

`/wire` invokes either **governance workspace wiring** (special case) or the **Wire Executor DAG** for code components.

## GOVERNANCE WORKSPACE (run first on new/existing repos)

Ensures `.cursor-commands` points at Dropbox GlobalCommands SSOT and `sessionEnd` backup hook is active.

```bash
# Check only (exit 1 if miswired)
bash "$HOME/Dropbox/Cursor Governance/GlobalCommands/ops/scripts/check_governance_wiring.sh" "$(pwd)"

# Repair + re-check (what /wire governance runs)
bash "$HOME/Dropbox/Cursor Governance/GlobalCommands/ops/scripts/wire_governance_workspace.sh" "$(pwd)"
```

**Aliases:** `/wire governance`, `/wire governance-workspace`, `/wire .cursor-commands`

**Does NOT use `wire_executor.py`.** Runs `setup_workspace_symlinks.sh` (symlinks + hook install) then `check_governance_wiring.sh`.

**Auto-chained from `/start-session`** when the check fails — session cannot proceed until PASS.

## CODE COMPONENT WIRING

## INVOCATION

```bash
python3 .cursor/workflows-synced/wire_executor.py <component>
```

## WHAT THE DAG DOES (AUTONOMOUS)

```
┌─────────────────────────────────────────────────────────┐
│  DISCOVERY        │ Find ALL references with rg        │
├─────────────────────────────────────────────────────────┤
│  ANALYSIS         │ Classify component type            │
├─────────────────────────────────────────────────────────┤
│  PLAN             │ Create surgical action list        │
├─────────────────────────────────────────────────────────┤
│  EXECUTE          │ Apply fixes (NO user confirmation) │
├─────────────────────────────────────────────────────────┤
│  VALIDATE         │ py_compile + import test           │
├─────────────────────────────────────────────────────────┤
│  RE-DISCOVERY     │ Confirm all refs fixed             │
├─────────────────────────────────────────────────────────┤
│  CONFIRM-WIRING   │ Full verification pass             │
├─────────────────────────────────────────────────────────┤
│  GENERATE-REPORT  │ GMP report via script              │
├─────────────────────────────────────────────────────────┤
│  COMMIT           │ Stage + commit (NO PUSH)           │
└─────────────────────────────────────────────────────────┘
```

## FEATURES

- **Fully autonomous** — No user confirmation gates
- **Protected file detection** — Auto-escalates to /gmp
- **Semantic refusals** — Blocks dangerous patterns
- **Auto-report** — Uses canonical report generator
- **Safe commit** — Commits locally, does NOT push

## USAGE

```bash
# Wire a module
python3 .cursor-commands/workflows/wire_executor.py core/tools/registry.py

# Wire by import path
python3 .cursor-commands/workflows/wire_executor.py memory.substrate_service

# Check status
python3 .cursor-commands/workflows/wire_executor.py --status

# Resume if interrupted
python3 .cursor-commands/workflows/wire_executor.py --resume

# Reset state
python3 .cursor-commands/workflows/wire_executor.py --reset
```

## STATE FILE

Execution state is persisted to `.wire_executor_state.json`

If interrupted, resume with `--resume`.

## PROTECTED FILES (AUTO-ESCALATE)

If these files need changes, executor auto-escalates to /gmp:
- `core/agents/executor.py`
- `runtime/websocket_orchestrator.py`
- `memory/substrate_service.py`
- `docker-compose.yml`
- `Dockerfile`

## OUTPUT

The executor produces:
1. Terminal progress for each step
2. GMP report at `reports/GMP-Report-*.md`
3. Local commit (no push)

## ENFORCEMENT

The DAG is MANDATORY. The slash command is just a trigger.

All step ordering, validation, and reporting is handled by the executor.

---
name: confirm-wiring
version: "2.0.0"
description: "Verify component is fully wired — no orphan refs, no runtime failures"
auto_chain: ynp
dag: confirm-wiring-v1
dag_file: .cursor-commands/workflows/dags/confirm_wiring_dag.py
---

# /confirm-wiring — Integration Audit

**DAG-ENFORCED.** Execute the `confirm-wiring-v1` DAG.

## Usage

```
/confirm-wiring core/tools/registry_adapter.py       # Verify a file
/confirm-wiring memory.consolidation                  # Verify a module
/confirm-wiring RegistryAdapter                       # Verify a component
```

## What It Does

1. **Resolve imports** — `python3 -c "from {package} import *"`
2. **Try-run** — `make try-run FILE={file}` (syntax + import + execution)
3. **Verify exports** — Check `__init__.py` exports
4. **Find consumers** — `rg` for all importers
5. **Verify tests** — Find and run tests

## Execution

```python
from .cursor_commands.workflows.dags.confirm_wiring_dag import CONFIRM_WIRING_DAG
# Follow each node's action field in sequence
```

The DAG contains all instructions. Follow each node's `action` field exactly.

## Flow

```
START → resolve_imports → try_run → verify_exports → find_consumers → verify_tests → report
```

## Key Files

- **DAG**: `.cursor-commands/workflows/dags/confirm_wiring_dag.py`
- **Try-Run**: `tools/validation/try_run.py`
- **Makefile**: `make try-run FILE=path`

---
name: governance
version: "1.0.0"
description: "Check and enforce governance rules"
auto_chain: ynp
---

# /governance — Governance Check

## WHAT IT DOES

Verify compliance with L9 governance:

1. Protected files respected
2. GMP phases followed
3. Approval gates passed
4. Audit trail exists

---

## CHECKS

### Protected Files

```
PROTECTED:
├── core/agents/executor.py
├── runtime/websocket_orchestrator.py
├── memory/substrate_service.py
├── docker-compose.yml
└── core/singleton_registry.py
```

Any modification → Requires KERNEL GMP

### GMP Compliance

| Requirement | Check |
|-------------|-------|
| Phase 0 plan locked | ✅ |
| No scope drift | ✅ |
| Validation passed | ✅ |
| Report generated | ✅ |

### Approval Gates

| Operation | Approval |
|-----------|----------|
| Protected file | Igor explicit |
| Destructive action | Igor explicit |
| Production deploy | Igor explicit |

---

## OUTPUT

```markdown
## 🛡️ GOVERNANCE CHECK

### Status: ✅ COMPLIANT | ❌ VIOLATIONS

### Protected Files
| File | Status |
|------|--------|
| executor.py | ✅ Untouched |

### GMP Compliance
| Check | Status |
|-------|--------|
| Plan locked | ✅ |

### Violations (if any)
| Violation | Location | Fix |
|-----------|----------|-----|
```

→ **Auto-chains to /ynp**

--- End Command ---

---
name: governance-backup
version: "1.0.0"
description: "Push GlobalCommands (.cursor-commands) to cryptoxdog/Cursor-Governance"
---

# /governance-backup — GitHub SSOT Backup

Dropbox `GlobalCommands/` is the **live SSOT**. This command commits and pushes it to [cryptoxdog/Cursor-Governance](https://github.com/cryptoxdog/Cursor-Governance).

## When to run

- End of every session (also runs automatically via `sessionEnd` hook after setup)
- After editing any file under `@.cursor-commands/`
- Before switching machines

## Command

```bash
bash .cursor-commands/ops/scripts/backup_to_github.sh
```

With message:

```bash
bash .cursor-commands/ops/scripts/backup_to_github.sh "chore(governance): describe change"
```

From PlasticOS repo:

```bash
make governance-backup
```

## Dry run (commit locally, no push)

```bash
GOVERNANCE_BACKUP_DRY_RUN=1 bash .cursor-commands/ops/scripts/backup_to_github.sh
```

## Skip automatic backup for one session

```bash
export GOVERNANCE_BACKUP_SKIP=1
```

## Requirements

- `git` and network access
- `gh auth login` (or SSH/credential helper configured for GitHub)
- Dropbox SSOT at `$HOME/Dropbox/cursor governance/GlobalCommands/`

## Setup (once per machine)

```bash
bash .cursor-commands/ops/scripts/setup_workspace_symlinks.sh
```

Installs `~/.cursor/hooks.json` sessionEnd hook + symlink to this backup script.

---

<!-- migrated-from: commands/rules.md -->

---
name: rules
version: "2.2.0"
description: "List ALL governance rules from .cursor/rules/ with status"
auto_chain: null
---

# /rules — Governance Rules (v2.1.0)

## EXECUTION

When `/rules` is invoked, read ALL `.mdc` files from `.cursor/rules/` and report:

### Step 1: Count and List

```bash
# Count total rules
ls .cursor/rules/*.mdc | wc -l

# List rules with alwaysApply: true
grep -l "alwaysApply: true" .cursor/rules/*.mdc | xargs -I{} basename {}

# List rules WITHOUT alwaysApply: true
grep -L "alwaysApply: true" .cursor/rules/*.mdc | xargs -I{} basename {}
```

### Step 2: Output Format

```markdown
## 📜 GOVERNANCE RULES

**Total:** {count} rules | **Always-Applied:** {count} | **Context-Only:** {count}

### ✅ Always-Applied Rules (loaded every session)

| # | File | Description |
|---|------|-------------|
| 1 | 00-global.mdc | L9 global rules |
| 2 | 30-odoo-native.mdc | Odoo-native patterns |
| ... | ... | ... |

### ⚠️ Context-Only Rules (loaded when matching globs)

| # | File | Trigger |
|---|------|---------|
| 1 | 10-lang-typescript.mdc | `**/*.ts` files |
| ... | ... | ... |

### 🔴 Rules Without Frontmatter (need fixing)

| # | File |
|---|------|
| 1 | ... |
```

---

## CRITICAL ODOO RULES (Always-Applied)

| File | Purpose |
|------|---------|
| `30-odoo-native.mdc` | ORM patterns, recordsets, domains, actions |
| `95-plasticos-equipment-policy.mdc` | Equipment wiring requirements |

---

## CRITICAL SAFETY RULES (Always-Applied)

| File | Purpose |
|------|---------|
| `01-git-push-prohibition.mdc` | NEVER push without explicit request |
| `96-git-push-approval.mdc` | Git push requires approval |
| `99-no-auto-commit.mdc` | Never auto-commit |
| `99-execute-as-instructed.mdc` | Execute exactly as instructed |
| `91-existing-code-source-of-truth.mdc` | Existing code wins |
| `92-learned-lessons.mdc` | Critical prevention rules |

---

## HOW TO ENABLE A RULE

Add this frontmatter to any `.mdc` file:

```yaml
---
description: "Brief description of the rule"
alwaysApply: true
---
```

Or for context-triggered rules:

```yaml
---
description: "Brief description"
alwaysApply: false
globs: ["**/*.py", "plasticos_*/**/*"]
---
```

---

## RULE CATEGORIES

| Prefix | Category | Examples |
|--------|----------|----------|
| `00-09` | Global | Core rules, git, slash commands |
| `10-29` | Language | Python, TypeScript |
| `30-39` | Framework | Odoo, React |
| `40-49` | Domain | Business logic |
| `50-59` | QA | Testing |
| `60-69` | Anti-patterns | What NOT to do |
| `70-79` | Workflow | CI/CD, reviews |
| `80-89` | GMP | Governance process |
| `90-99` | Protection | Lessons, policies |

---

<!-- harvested-from: infrastructure-security-audit + infrastructure-credentials-manage (Suite-5 legacy) -->

# Secret & Credential Hygiene (manual cross-check)

A fast manual pass that **complements** automated CI (gitleaks, semgrep, `security.yml` pip-audit/Trivy, pre-commit secret hooks). Run when touching configs, env files, DSNs, or new integrations. Enforces the PlasticOS hard rule *"No credentials in code"*.

## Secret patterns to flag

| Pattern | Indicates |
|---------|-----------|
| `API_KEY = "..."` / `password: "..."` | Hardcoded secret literal |
| `sk-...` | OpenAI / LLM API key |
| `xoxb-...` / `xoxp-...` | Slack token |
| `ghp_...` / `gho_...` | GitHub token |
| `AKIA...` | AWS access key id |
| `postgresql://user:pass@host` | DB credentials in URL/DSN |
| `-----BEGIN ... PRIVATE KEY-----` | Private key material |

## Severity matrix

| Severity | Examples | Action |
|----------|----------|--------|
| 🔴 Critical | Live key/secret in tracked code | Block; rotate the secret immediately |
| 🟡 High | Secret in history or logs | Fix before merge |
| 🟠 Medium | Exposed endpoint missing rate-limit / input validation | Review |
| 🟢 Low | Verbose error messages, no request-id tracking | Optional |

## Env-var hygiene checklist

- [ ] All credentials read from env / system params — never literals
- [ ] No placeholders left in code (`YOUR_API_KEY`, `API_KEY_HERE`, `CHANGEME`)
- [ ] `.env*` is in `.gitignore`; an `.env.example` documents required vars
- [ ] Logs are sanitized — no secrets in log output
- [ ] Secrets confirmed absent from committed history for the touched files

Fail closed: if a 🔴 is found, stop and surface it before any commit/push.
