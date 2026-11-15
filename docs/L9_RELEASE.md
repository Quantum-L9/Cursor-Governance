# `make release` — front door to Core's release engine

The release engine and the release runner are Core's: `tools/l9_release`
(`plan` / `build` / `publish` / `verify`, declaration schema `l9.release/v1`) and
`.github/workflows/release-runner.yml` in Quantum-L9/l9-ci-core
(docs/RELEASING.md there). Cursor-Governance holds no engine code and never tags
or publishes. `make release` is only the operator's entry point to them, used
like `make pr`:

```bash
l9 release                 # Core engine `plan` (read-only): what would be released
l9 release DRY_RUN=1       # `plan` + reproducible `build`, locally; publishes nothing
l9 release DISPATCH=1      # workflow_dispatch Core's release runner for this repository
make -C "$HOME/.cursor-governance" release WS="$PWD" [DRY_RUN=1] [DISPATCH=1]
```

| Piece | Path |
|---|---|
| Make target | `ops/make/release.mk` (composed by `Repo.mk`; `release` is CONSUMER_SAFE) |
| Front door | `ops/scripts/l9_release.py` |
| Core pin | `ops/config/release-core.json` |
| Tests | `tests/ops/scripts/test_l9_release.py` |

## Core resolution

`ops/config/release-core.json` pins Core by exact commit, the way Cursor-Governance
pins every other Core tool (workflow `uses:` SHAs, `ops/ci_parity/tools.yaml`). The
front door fetches exactly that commit into
`${XDG_CACHE_HOME:-~/.cache}/l9-release/core/<sha>`, verifies `HEAD` and the presence
of `tools/l9_release`, and reuses the cache afterwards. A revision that is not
fetchable is a transport failure (exit 3); one that lacks the engine is refused
(exit 1). Re-pinning is a one-line change to `revision`.

## Modes

| Mode | What runs |
|---|---|
| default | `python -m tools.l9_release --workspace WS --repository <origin slug> plan` |
| `DRY_RUN=1` | `plan`, then `build --out … --scratch … --phases run` (Core runs the repository's make-v1 phases and two reproducible build rounds). Artifacts land in `${XDG_CACHE_HOME:-~/.cache}/l9-release/build/<owner>__<name>/<commit>/dist`, outside the workspace. |
| `DISPATCH=1` | `POST repos/Quantum-L9/l9-ci-core/actions/workflows/release-runner.yml/dispatches` with `ref=main` and `inputs.repository=<origin slug>` over `gh api` (REST), then prints the run URL. |

`DRY_RUN=1` and `DISPATCH=1` are exclusive. The engine runs with Core as its
working directory and with the governance invocation state removed from its
environment (`MAKEFLAGS`, `PYTHON`, `PYTHONPATH`, `VIRTUAL_ENV`, `UV_PROJECT`,
`UV_PROJECT_ENVIRONMENT`, …), so the released repository's own phases never see
the governance interpreter or uv project. The engine's own `plan` needs
`GH_TOKEN`/`GITHUB_TOKEN` for the Releases API; the front door passes the caller's
environment through and adds no credential.

Exit codes: the engine's (`0` done, `1` refused by a precondition, `2` tool,
transport or contract failure); the front door adds `1` for its own input checks and
`3` when Core cannot be fetched or the dispatch is refused.

## Publication

Publication is Core's release runner, under the authority Core configures for it
(`release-runner` environment, per-repository App token). `DISPATCH=1` asks it to
run; it does not grant or carry any publication authority itself. A repository
releases only once it carries a `.l9/release.json` that conforms to Core's
`l9.release/v1` (`tools/l9_release/release.schema.json` in Core).
