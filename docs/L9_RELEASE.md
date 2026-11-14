# `make release` — one release command for every L9 repository

`make release` is the sibling of `make pr`. It lives upstream in Cursor-Governance
and releases any L9 repository from a clean `origin/main` commit. No workflow is
copied into consumers; a consumer adds one declaration file.

```bash
l9 release [VERSION=X.Y.Z] [DRY_RUN=1]
make -C "$HOME/.cursor-governance" release WS="$PWD" [VERSION=X.Y.Z] [DRY_RUN=1]
make -C "$HOME/.cursor-governance" release-declaration-check WS="$PWD"   # read-only
```

| Piece | Path |
|---|---|
| Make target | `ops/make/release.mk` (composed by `Repo.mk`; `release` is CONSUMER_SAFE) |
| Command | `ops/scripts/l9_release.py` |
| Declaration loader / validator | `ops/scripts/release_declaration.py` |
| Declaration schema | `ops/schemas/l9.release.v1.schema.json` |
| Reproducibility | `ops/scripts/release_reproducible.py` |
| Examples | `docs/examples/release/*.release.json` |
| Tests | `tests/ops/scripts/test_l9_release.py` |

## Declaration: `<repo>/.l9/release.json` (`l9.release/v1`)

```json
{
  "schema": "l9.release/v1",
  "repository": "Quantum-L9/l9-constellation-topology",
  "default_branch": "main",
  "ecosystems": [{ "kind": "python-uv", "version_authority": "pyproject.toml" }],
  "artifacts": [
    "l9_constellation_topology-{version}-py3-none-any.whl",
    "l9_constellation_topology-{version}.tar.gz"
  ],
  "major_tag": "none",
  "notes": { "changelog": "CHANGELOG.md" },
  "pre_release": { "argv": ["uv", "run", "python", "scripts/validate_release_readiness.py"] }
}
```

| Field | Meaning |
|---|---|
| `repository` | `owner/name`; must equal the workspace's `origin`. |
| `default_branch` | Branch a release is cut from (default `main`). |
| `ecosystems[]` | `python-uv` (`pyproject.toml` `[project].version`, static) or `node-npm` (`package.json` `.version`). All authorities must agree. |
| `artifacts[]` | Exact asset names, `{version}` substituted. The build must produce exactly this set. |
| `major_tag` | `none`, or `advance` (maintain `vN`). |
| `notes.changelog` | Changelog with a dated `## X.Y.Z - YYYY-MM-DD` section, used as the Release notes. |
| `pre_release.argv` | Optional repository gate, run after the make-v1 phases. argv list, never a shell string. |

Absent declaration → `DECLARATION_INVALID` naming the file to add. Repositories that
ignore `.l9/*` must re-include it (`!.l9/release.json`).

## Stages

1. **Declaration** — load and validate.
2. **Preflight (fail-closed)** — worktree clean (outputs under `.l9/release/`
   excepted); `HEAD` equals freshly fetched `origin/<default>`; zero open PRs into it
   (REST `gh api`); version authorities agree, equal `VERSION` when given, and are
   strictly greater than the latest exact `vX.Y.Z` tag; `vX.Y.Z` absent remotely;
   dated CHANGELOG section present.
3. **Gate** — `make setup validate check test` and the declared `pre_release.argv`
   in a separate clean checkout of the commit, with the governance Make state
   (`MAKEFLAGS`, `PYTHON`, `VIRTUAL_ENV`, …) stripped from the environment.
4. **Reproducible build** — two independent clean checkouts, `SOURCE_DATE_EPOCH` =
   commit time. `python-uv`: `uv build`; `node-npm`: `npm pack`. Every artifact must
   be byte-identical across the two builds. The one permitted repair is the setuptools
   sdist envelope (below). Assets and `SHA256SUMS` land in `.l9/release/vX.Y.Z/`.
   **`DRY_RUN=1` stops here.**
5. **Publish** — requires publication authority (below). Annotated tag `vX.Y.Z` at
   exactly the commit (`git tag -s` when `user.signingkey` is configured, otherwise
   `-a`, and the receipt and notes say which); plain push of that one ref. With
   `major_tag: advance`: `vN` is created when absent; when it already points at an
   ancestor, the exact `--force-with-lease` command is handed to the operator
   (`COMPLETION_REQUIRED`) — `make release` never force-pushes, never moves an
   existing tag, never goes backwards. Then
   `gh release create vX.Y.Z --verify-tag` with the CHANGELOG section, a provenance
   block (commit, `SOURCE_DATE_EPOCH`, build environment, SHA-256 table) and the
   assets plus `SHA256SUMS`.
6. **Verify** — Release exists, is not a draft, carries exactly the assets;
   re-download, `sha256sum -c SHA256SUMS`, downloaded `SHA256SUMS` equals the built
   one; remote tag peels to the commit. Receipt: `.l9/release/release-receipt.json`
   (`l9.release-receipt/v1`, local, uncommitted), written for every outcome.

Exit codes: `0` RELEASED / DRY_RUN_PASS · `1` REFUSED / UNAUTHORIZED · `2`
DECLARATION_INVALID · `3` TRANSPORT_BLOCKED · `4` NOT_REPRODUCIBLE · `5`
COMPLETION_REQUIRED · `6` VERIFY_FAILED.

Never: npm or PyPI publication, force-push, moving or deleting an existing exact tag.

## Reproducibility method

setuptools does not apply `SOURCE_DATE_EPOCH` to sdist tar members: the wheel is
reproducible, the sdist differs in member mtimes and the gzip header mtime. When —
and only when — the two sdists differ, both are rewritten with only the archive
envelope normalised: members sorted, mtime = `SOURCE_DATE_EPOCH`, uid/gid 0,
uname/gname empty, gzip header mtime 0 and no file name. Names, types, modes, link
targets and bytes are carried over; the per-member content digest (type, mode,
sha256 of the bytes) is computed before and after and must be identical, and the
two normalised archives must then be byte-identical, or the release refuses.

Evidence, `Quantum-L9/l9-constellation-topology` @ `89150bdef6057913f1037aff4d973033de72c224`
(`SOURCE_DATE_EPOCH=1794678803`), through `stage_build`:

| Artifact | Build A | Build B | Released |
|---|---|---|---|
| wheel | `c6f4eea0…8028` | `c6f4eea0…8028` | `c6f4eea0e9a1ce46caa7f310da28032a0d3b4be0ee9b6483bee26e1dd08b8028` |
| sdist (raw) | `ed238183…c631` | `f8721c9b…279c` | — |
| sdist (normalised, 256 members, contents unchanged) | `4555bcd2…0e89` | `4555bcd2…0e89` | `4555bcd2d9b601f52f61f61c1049e82af4836fdd66c2094996fcc781404b0e89` |

A second, separate pair of builds normalised to the same `4555bcd2…` digest.

## Publication authority

A release pushes a tag ref, a first publication outside `make pr`
(CANONICAL_LAW §6.2.8). `make release` uses the existing operator authority for that
push — the publish-path breakglass receipt (`ops/autonomy/breakglass_receipt.py`;
`skills/l9-release-publication/references/publication-plane.md`). It must be in force
and its reason must name the exact tag and commit:

```bash
"$GOV/.venv/bin/python" "$GOV/ops/autonomy/breakglass_receipt.py" --write --issuer ops --hours 1 \
  --reason 'make release v3.0.0 89150bdef6057913f1037aff4d973033de72c224'
```

Without it the command stops with `UNAUTHORIZED` after the build. A hosted session
whose transport refuses the tag push or Release creation stops with
`TRANSPORT_BLOCKED` and prints the operator commands; assets and `SHA256SUMS` stay in
`.l9/release/vX.Y.Z/`.

## First use: l9-constellation-topology v3.0.0

In the topology repository, add `.l9/release.json` from
`docs/examples/release/l9-constellation-topology.release.json` through its own PR,
then from a clean checkout of the merged `main`:

```bash
l9 release VERSION=3.0.0 DRY_RUN=1
# operator: breakglass receipt naming v3.0.0 and the release commit
l9 release VERSION=3.0.0
```

Adding the declaration moves `main` past `89150bd`; the release commit is the new
tip, and the receipt records it.
