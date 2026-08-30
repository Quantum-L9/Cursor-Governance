# Claude surface parity matrix

Every Claude cloud surface — Desktop (Cloud mode), Mobile, Web, and
`claude --cloud` CLI — bootstraps the **same** governance adapter
(`environment/agents/adapters/claude-code/`) against the **same** ephemeral
runtime clone of `Quantum-L9/Cursor-Governance`. They therefore share one
environment contract. Cursor shares the same *behavioral* contract (same rules,
skills, commands, governance revision) but a **different transport**
implementation (Cursor loads `.mdc` rules through the `l9-governance` plugin;
Claude mounts the projected `.md` tree at `.claude/rules`).

Expected, per `l9.claude_operational_parity_convergence.v1`:

- Claude cloud surfaces share one environment contract → **true**
- Cursor shares the behavioral contract → **true**
- Cursor and Claude share the transport implementation → **false**

## The one contract (shared across all Claude cloud surfaces)

| Axis | Contract | Authority |
|---|---|---|
| Canonical governance revision | GitHub default branch `main`, resolved live | `origin/main`; readiness `governance_SHA` |
| Enabled skills | projected per-skill symlinks from the skill registry | `claude_projection.py` (skills) |
| Enabled commands | per-command symlinks from `commands/COMMANDS_MANIFEST.yaml` | `claude_projection.py` (commands) |
| Rules contract | `environment/generated/llm-rules/**` mounted at `.claude/rules` | `claude_projection.py` (rules) |
| Plugin required state | Desktop: `plugins.desired.json` (core + desktop_only). Hosted: marketplace skip is READY, not a required plane. | `claude_projection.py` (plugins) |
| MCP contract | `.mcp.json` is a projection of `mcp.template.json` (single MCP authority) | `claude_projection.py` (mcp) |
| Memory backend | Cursor Graphiti front door only (`ops/graphiti`); no side door | rule 03; CANONICAL_LAW §8 |
| Graphiti capability | HTTPS Graphiti (`GRAPHITI_MCP_URL`); `memory.cli` vs `memory.mcp`; broker retired | `emit_claude_readiness.py` graphiti probe; adapter `mcp.template.json` |
| Secret boundary | `model-controlled` — no broker/Infisical/Graphiti secret on the surface | `verify_account_env.py` prohibited set |
| Makefile facade | one Governance Makefile; `l9` dispatcher exposes CONSUMER_SAFE targets | `L9_CONSUMER_SAFE_TARGETS`; `docs/L9_DISPATCHER.md` |
| PR validation | governance Makefile `pr` via `l9 pr` / `make -C "$GOV" pr WS="$PWD"` → `open_pr_after_gate.sh` (REST); changed-files gate; consumer repo needs no local `pr` target. Same finish as Cursor: authorize-release then `PR_REMEDIATE=0 make pr` / `l9 pr`. Cursor skips tree kernels; this adapter still fires them. | governance Makefile `pr` / `pr-check` (`docs/L9_DISPATCHER.md`); Profile `session_start_block` |
| Push authority | available when repo release law + L4 release receipt allow | `l4_local.py`; `open_pr_after_gate.sh` |
| Merge authority | no standing env boolean; scoped, expiring receipt or human breakglass | `merge_gate.py`; `authorize_merge.py` |
| Readiness schema | `l9.claude-readiness.v1` (this repo) | `emit_claude_readiness.py` |

## Parity matrix (E2E observation)

`E2E result` is **OBSERVED** only when this execution environment can actually
launch or inspect that surface. A surface this environment cannot drive is
**BLOCKED pending real execution** — never marked PASS from config files alone
(contract `external_surface_rule`, stop condition
`do_not_claim_mobile_desktop_web_parity_without_runtime_evidence`).

| Surface | Environment contract | Transport | E2E result | Evidence |
|---|---|---|---|---|
| `claude --cloud` CLI | shared (above) | Claude adapter → runtime clone | **OBSERVED** | this session; live readiness receipt |
| Claude Desktop (Cloud) | shared (above) | Claude adapter → runtime clone | **BLOCKED** | not launchable from here — run the probe below |
| Claude Mobile | shared (above) | Claude adapter → runtime clone | **BLOCKED** | not launchable from here — run the probe below |
| Claude Web | shared (above) | Claude adapter → runtime clone | **BLOCKED** | not launchable from here — run the probe below |
| Cursor (reference) | shared behavioral contract | Cursor plugin (`.mdc`); **different transport by design** | **BLOCKED** | not launchable from here — run the probe below |

### Observed surface: `claude --cloud` CLI (this session)

The live readiness receipt (`~/.l9/claude/readiness-receipt.json`, schema
`l9.claude-readiness.v1`) is the evidence. On this hosted surface it reports
`overall_readiness = DEGRADED`: the structural contract (projection, Makefile
facade, dispatcher, merge-authority posture, secret boundary) is READY, while
the capability dimensions (MCP loaded, authenticated Graphiti) are DEGRADED
because the platform issues no broker-verifiable session identity — a
`BLOCKED_BY_EXTERNAL_DEPENDENCY` documented in `docs/DEGRADED_MODE_CONTRACT.md`,
not a parity defect. Parity is judged on the **contract** fields, which match.

## Parity probe procedure (run on each BLOCKED surface)

On the surface under test, once its SessionStart has run:

```bash
# 1. Emit that surface's readiness receipt (or read the one SessionStart wrote).
make -C "$HOME/.cursor-governance" claude-readiness

# 2. Capture the machine-readable receipt.
cat ~/.l9/claude/readiness-receipt.json
```

The surface **passes parity** when its receipt shows, against the `claude --cloud`
reference:

- the same `governance_repository` and `governance_default_branch`;
- `governance_SHA` freshness READY (or an equal SHA);
- `skill_/command_/rule_projection_status`, `settings_status`, `hooks_status`
  all READY;
- the same MCP contract (`.mcp.json` a projection of `mcp.template.json`);
- `merge_authority_status = READY` (no environment boolean authorizes merge);
- `secret_boundary_status = READY` (`model-controlled`);
- `Makefile_facade_status = READY` and `dispatcher_status = READY`;
- `interpreter_importable_status = READY` (the governance locked interpreter
  imports the core deps — an unimportable environment is DEGRADED, never READY);
- `schema_version = l9.claude-readiness.v1`.

Capability dimensions (`MCP_status`, `Graphiti_authenticated_health`) may read
DEGRADED where the platform issues no identity; that is a shared, expected
degraded mode across the cloud surfaces, not a parity divergence. Record the
receipt from each surface here as it is observed; until then those surfaces stay
**BLOCKED pending real execution**.

## Completion status

Repository-side convergence is COMPLETE and its evidence is the passing test
suites and the observed `claude --cloud` receipt. Cross-surface certification is
**PARTIALLY_COMPLETE**: Desktop, Mobile, Web, and Cursor E2E parity is BLOCKED
pending real execution on those surfaces, per the probe above.
