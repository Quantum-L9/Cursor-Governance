# CLAUDE.md — authority pointer

This file is deliberately compact: it names the binding authorities and the few
safety rules that must be available before deeper repository documentation loads.
It is **not** a second doctrine source.

## Authority chain

Read and apply these in order; a lower source never overrides a higher source.

1. [`CANONICAL_LAW.md`](CANONICAL_LAW.md) — binding governance, trust, memory,
   publication, and secret-plane law. Read it before changing those surfaces.
2. [`ops/autonomy/surface_profile.yaml`](ops/autonomy/surface_profile.yaml) —
   standing authority for the exact surface identifier `claude-code`. A variant
   identifier can remove the session from its declared authority.
3. [`AGENTS.md`](AGENTS.md) — repository operating instructions and activation
   contract.
4. [`skills/l9-*`](skills/) — task-scoped procedures invoked when their routing
   conditions apply.
5. Agent-invented contracts — **no authority**. Propose a governed change through
   the sources above instead of silently creating a rule.

Useful maps, not competing authority: [`ARCHITECTURE.md`](ARCHITECTURE.md),
[`INVARIANTS.md`](INVARIANTS.md), and
[`ORG_INVARIANTS.yaml`](ORG_INVARIANTS.yaml).

## Immediate operating directives

- **Memory:** hydrate through `python -m ops.memory.cli hydrate`; never create or
  write `memory-bank/`.
- **Activation:** SessionStart is the only activation path. Follow `AGENTS.md`
  for activation and repair, not an ad hoc bootstrap.
- **Publication:** use `PR_REMEDIATE=0 make pr`. Do not use `make push`, raw
  first-publication `git push`, `gh pr create`, or MCP push/PR-creation tools.
- **Credentials:** this model-controlled surface holds no raw credentials. Never
  paste a token or bearer when a capability is unavailable; use
  [`docs/DEGRADED_MODE_CONTRACT.md`](docs/DEGRADED_MODE_CONTRACT.md).
- **Verification:** this repository intentionally has no local commit hook. Do
  not use bypass flags or variables (`--no-verify`, `SKIP`, `HUSKY`, or altered
  hooks paths). Use `make pr` or `OPEN_PR=0 make pr` for diagnostics.
- **Failures:** treat every failure as evidence. Reproduce in isolation, baseline
  against unmodified `main`, identify any shared state, then classify or repair.
  “Pre-existing” is not a resolution.
- **Receipts:** inspect current bootstrap and refresh state with
  `python3 ops/scripts/claude_bootstrap_receipt.py` and
  `python3 ops/scripts/governance_refresh_receipt.py`; absent is never ready.
- **Destructive work:** inspect and name an explicit target list first; never use
  a glob or an unreviewed variable expansion. The detailed policy and exceptions
  remain in `CANONICAL_LAW.md` and `AGENTS.md`.

## Readiness and document ownership

```bash
make claude-env
```

`STRUCTURAL_PASS` means files are correct; the `RUNTIME:` line determines whether
this session actually loaded them. Root-document protection and ownership are
owned by [`ops/config/root-file-protection.json`](ops/config/root-file-protection.json)
and `AGENTS.md` §14. Read those sources before changing protected root files.

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
