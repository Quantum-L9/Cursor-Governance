# Execution contracts (first-class)

Cursor-primary home for L9 execution-architecture **contracts and templates**.

| Path | Role |
|------|------|
| [`MANIFEST.yaml`](MANIFEST.yaml) | Registry of first-class artifacts in this tree |
| [`templates/canonical.template.executable_plan.v1.plan.md`](templates/canonical.template.executable_plan.v1.plan.md) | Executable Cursor `.plan.md` template (PE + autonomy) |
| [`templates/canonical.template.executable_plan.v1.plan.md.meta.md`](templates/canonical.template.executable_plan.v1.plan.md.meta.md) | Primitive metadata sidecar |

Related schema (still WIP until promoted):  
`WIP/Execution Schemas/environment/contracts/execution/schemas/canonical.schema.plan_document.v1.yaml`

## Law

- This directory is **repo SSOT** for registered templates.
- Skill/command paths may **symlink or project** here; they must not fork a second body.
- `.cursor/plans/` is a local IDE mirror only — never the git SSOT (`.cursor/` is gitignored).

## Execute path for template instances

```text
.plan.md instance
  → @environment/program-execution
  → @autonomy (subordinate Program lease)
  → PE adapter
```

See `environment/agents/PEER_EXECUTION.md`.
