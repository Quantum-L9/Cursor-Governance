# Sonar FP — LLM/CLI path-escape on optimize-cli-pr-pack scripts

## Status

Residual SonarCloud New Code Security findings on this skill's `scripts/`
directory after real confinement. Same class as `environment/agents/tools/`
(PR #25).

## Mitigations in code

| Rule | Mitigation |
|------|------------|
| `S8707` | `route_optimize.py` is stdin→stdout only (no filesystem path CLI args) |
| `S2083` | `write_text(root, path, …)` with `under_root` / `commonpath` before `open` |
| `S6096` | Archive via `under_root` + BytesIO (create-only; no extract path join) |
| `S6350` | Tracked `git diff` uses `--pathspec-from-file=-`; untracked uses fixed staging basename |

## Gate workaround

`sonar-project.properties` excludes `**/skills/optimize-cli-pr-pack/scripts/**`
(and `**/environment/agents/tools/**`). Do **not** use `NOSONAR`.
