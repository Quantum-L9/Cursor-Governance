# Sonar FP — LLM/CLI path-escape on optimize-cli-pr-pack scripts

## Status

Residual SonarCloud New Code Security findings on this skill's `scripts/`
directory after real confinement. Same class as `environment/agents/tools/`
(PR #25). Note: Automatic Analysis still indexes excluded paths; `sonar.exclusions`
alone did not drop findings on this PR — code-level sink removal is required.

## Mitigations in code

| Rule | Mitigation |
|------|------------|
| `S8707` | `route_optimize.py` is stdin→stdout only (no filesystem path CLI args) |
| `S2083` | `write_text(root, path, …)` with `under_root` / `commonpath` before `open` |
| `S6096` | Archive via `under_root` + BytesIO (create-only; no extract path join) |
| `S6350` | Tracked: `git diff <base>` with **no path argv**, then filter allowlisted paths; untracked: fixed staging basename on argv |

## Gate workaround

`sonar-project.properties` still lists exclusions for documentation parity with
PR #25. Do **not** use `NOSONAR`.
